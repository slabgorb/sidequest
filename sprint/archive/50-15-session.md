---
story_id: "50-15"
epic: "50"
workflow: "tdd"
---
# Story 50-15: Journal: UI fact_id respect — drop synthetic id, consume narrator-supplied Footnote.fact_id (seam C UI part 1 per ADR-100)

## Story Details
- **ID:** 50-15
- **Epic:** 50 (Pingpong-archive triage and dropped-work cleanup)
- **Workflow:** tdd
- **Stack Parent:** 50-14 (Journal: JOURNAL_REQUEST handler) — complete

## Description

The Journal UI currently generates synthetic IDs for Footnote items instead of consuming the `fact_id` supplied by the narrator in structured output. This story implements **Seam C (UI part 1)** of ADR-100's Journal Pipeline Coherence design: respect the narrator-supplied `fact_id` field from the JOURNAL_RESPONSE payload, drop the synthetic ID generation, and wire the fact directly to the narration consumer flow.

## Acceptance Criteria

1. **Drop synthetic ID generation:** Remove any synthetic ID creation logic in useStateMirror or Journal components; fact identity is narrator-supplied only
2. **Consume Footnote.fact_id:** Hook the incoming JOURNAL_RESPONSE payload's `Footnote.fact_id` field into the Journal entry render path
3. **Type alignment:** Ensure TypeScript types match the narrator's fact_id string format (no coercion or transformation)
4. **Integration test:** Vitest covers the state-mirror update path with a real JOURNAL_RESPONSE fixture; verify fact_id flows through to Journal component without synthetic ID
5. **Wiring test:** End-to-end test from useWebSocket→JOURNAL_RESPONSE→state-mirror→Journal confirms fact_id is rendered and reachable from production code

## Workflow Tracking

**Workflow:** tdd  
**Phase:** finish  
**Phase Started:** 2026-05-14T09:47:48Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-14T00:00:00Z | 2026-05-14T09:28:56Z | 9h 28m |
| red | 2026-05-14T09:28:56Z | 2026-05-14T09:34:36Z | 5m 40s |
| green | 2026-05-14T09:34:36Z | 2026-05-14T09:37:50Z | 3m 14s |
| review | 2026-05-14T09:37:50Z | 2026-05-14T09:47:48Z | 9m 58s |
| finish | 2026-05-14T09:47:48Z | - | - |

## Sm Assessment

**Story shape:** Small, well-scoped UI story (2pt) that completes Seam C UI part 1 of ADR-100's Journal pipeline. Stack parent 50-14 (JOURNAL_REQUEST handler) merged in 46a0de8 — the wire is hot from server side. This story consumes what 50-14 produces.

**Scope boundary:** UI-only. Story 50-16 (confidence propagation) is the sibling that follows; do not absorb it. Story 50-17 (KnownFact.confidence enum) is a separate server-side promotion and out of scope here.

**Confidence:** ACs are crisp and verifiable. AC4+AC5 enforce both unit + wiring coverage per project rule "Every Test Suite Needs a Wiring Test."

**Risk:** Watch for type drift between the server's `Footnote.fact_id` (string per ADR-100) and the existing UI's synthetic ID shape. The Caterpillar should grep both sides before writing tests to lock the contract.

**Handoff to The Caterpillar (TEA):** Write failing tests for all 5 ACs in `sidequest-ui`. Branch `feat/50-15-journal-ui-fact-id` is ready off develop. Real JOURNAL_RESPONSE fixture should mirror the payload shape 50-14 emits — check sidequest-server tests for the canonical fixture.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Behavioral change to a wired hook with multiple ACs and a known load-bearing bug; pure-chore bypass does not apply.

**Test Files:**
- `sidequest-ui/src/hooks/__tests__/useStateMirror-50-15-fact-id.test.tsx` — 10 tests across all 5 ACs

**Tests Written:** 10 tests covering 5 ACs

**Status:** RED (9 failing, 1 passing — the App.tsx wiring import check, kept as a non-vacuous anchor per "Verify Wiring, Not Just Existence")

### Per-AC Coverage

| AC | Test(s) | Status |
|----|---------|--------|
| AC1 drop synthetic id | `uses narrator-supplied fact_id verbatim`, `does NOT produce ${turn}-${marker} synthetic id` | failing |
| AC2 consume Footnote.fact_id (per-fact dedupe) | `does not duplicate a fact across two turns`, `keeps distinct fact_ids as distinct` | failing |
| AC3 type alignment | `FootnoteData.fact_id is typed as string`, `useStateMirror does not own a local FootnoteData shadow` | failing |
| AC4 integration (NARRATION ↔ JOURNAL_RESPONSE) | `NARRATION+JOURNAL_RESPONSE collapse to one entry`, `preserves fact_id exactly` | failing |
| AC5 wiring | `useStateMirror imported by App.tsx`, `end-to-end NARRATION fact_id reaches knowledge[]` | 1 passing (import), 1 failing (round-trip) |

### Rule Coverage (TypeScript lang-review)

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 type-safety escapes (no `as any`) | All tests use typed `FootnoteData` / `GameMessage` — no escape hatches | enforced |
| #4 null/undefined handling | AC3 `FootnoteData.fact_id` typed `string \| undefined` — test passes explicit string, no `\|\|` coercion | enforced |
| #5 module/declarations (no shadow types) | AC3 test 2 grep-asserts the local `interface FootnoteData` shadow is removed and canonical is imported | failing (drives fix) |
| #8 test quality (no vacuous assertions) | Every test has at least one `expect().toBe/toContain/toMatch` against meaningful values; self-checked | enforced |
| #6 React hooks deps | AC5 round-trip uses `rerender` with `initialProps` shape — exercises `useStateMirror`'s `useEffect` deps without infinite loop | enforced |

**Rules checked:** 5 of 13 TypeScript checks are applicable to this hook's diff surface; remaining 8 (e.g., enum-patterns, async/promise, build-config) don't apply to a synchronous reactive hook.

**Self-check:** No vacuous assertions found. All `expect()` calls assert against concrete values or fail-loud regex patterns (synthetic-id detector). The single passing test in RED is the App.tsx wiring import check — non-vacuous (would fail if someone deleted the import).

### Notes for The White Rabbit (Dev)

1. The canonical `FootnoteData` in `src/types/payloads.ts:18` already has `fact_id?: string`. The hook redeclares a local `FootnoteData` (line 31-36) that omits `fact_id` — this shadow is the root cause. Drop the local interface, import the canonical type.
2. Line 186 currently: `const factId = \`${turnCounter}-${fn.marker ?? knowledge.length}\`;`. Replace with `fn.fact_id` consumption. Fallback policy is a Dev call — SOUL "no silent fallbacks" suggests warning + skip when `fact_id` is missing, but the protocol field is `Optional[str]` (server may omit), so a defensive synthetic fallback is also defensible. **Do not silently re-introduce `${turn}-${marker}`** — if you keep a fallback, log loudly so the GM panel sees it.
3. The JOURNAL_RESPONSE path (line 130-155) already does this correctly; the fix is solely on the NARRATION path (line 182-198).
4. **Scope discipline:** Do NOT touch the hardcoded `confidence: 'Suspected'` at line 194 — that is story 50-16's job. Do NOT promote KnownFact.confidence to a Literal — that is 50-17.

**Handoff:** To The White Rabbit (Dev) for the green phase.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-ui/src/hooks/useStateMirror.ts` — drop local `FootnoteData` shadow, import canonical from `../types/payloads`; consume `fn.fact_id` directly; loud-skip when missing
- `sidequest-ui/src/hooks/__tests__/useStateMirror-50-15-fact-id.test.tsx` — TEA's 10-test suite (no changes by Dev)

**Tests:** 10/10 passing (GREEN) in the new suite; regression check on related `useStateMirror-protocol26-7` (10/10) and `narration-screen-streaming` (8/8) clean.

**Lint/Typecheck:** Clean (eslint and `tsc --noEmit` both no output).

**Diff size:** 16 insertions / 12 deletions in `useStateMirror.ts`. Minimal, scope-bound. Confidence hardcode at line 194 untouched (50-16 territory). Local interface removed; canonical import substituted on existing import line.

**Branch:** `feat/50-15-journal-ui-fact-id` pushed.

**Handoff:** To The Queen of Hearts (Reviewer) for the review phase.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|------------|----------|--------|----------|----------|
| 1 | reviewer-preflight | yes | YELLOW | 28 pre-existing `@local/dice-lib` failures from commit `1e4a425`; 50-15 test file 10/10 pass; eslint + tsc clean | Confirmed: pre-existing, not introduced by 50-15. Logged as Delivery Finding for follow-up. |
| 2 | reviewer-edge-hunter | n/a | Skipped | disabled | N/A — `workflow.reviewer_subagents.edge_hunter: false` |
| 3 | reviewer-silent-failure-hunter | n/a | Skipped | disabled | N/A — disabled |
| 4 | reviewer-test-analyzer | yes | findings | 2 high (vacuous), 1 high (missing drop-path coverage), 4 medium | High findings: FIXED inline (drop-path tests added, vacuous removed, regex relaxed). Medium #4 (fact_id + missing summary) and #7 (AC4 content-precedence): deferred — beyond 50-15 scope. |
| 5 | reviewer-comment-analyzer | yes | findings | 2 high (stale RED-state framing, stale line refs), 2 medium (stale AC3 line ref, missing docblock contract) | All four FIXED inline. |
| 6 | reviewer-type-design | n/a | Skipped | disabled | N/A — disabled |
| 7 | reviewer-security | n/a | Skipped | disabled | N/A — disabled |
| 8 | reviewer-simplifier | n/a | Skipped | disabled | N/A — disabled |
| 9 | reviewer-rule-checker | yes | findings | 4 high (rule #1 type-fork casts, rule #5 GameStateProvider/payloads type fork, rule #8 vacuous `as GameMessage[]`, rule #8 fragile AC5 regex) | Rule #1/#5 type-fork findings: PRE-EXISTING, deferred + logged as Delivery Finding. Rule #8 `as GameMessage[]`: FIXED. Rule #8 fragile regex: FIXED (already by test-analyzer overlap). |

## Reviewer Assessment

**Verdict:** APPROVED with inline fixes applied (final commit `8be6ffe`).

### Rule Compliance (TypeScript lang-review, 13 checks)

| Check | Status | Note |
|-------|--------|------|
| #1 type-safety escapes | pass (within 50-15 scope) | The diff introduces no new `as any`, `!`, or `@ts-ignore`. Pre-existing `as FactSource`/`as Confidence` casts at lines 197-198 and `as unknown as NarrationMessage` at line 212 are documented as upstream findings. |
| #2 generics/interfaces | pass | No `Record<string,any>` or `Function` types. |
| #3 enums | pass | MessageType used as runtime values; no const-enum. |
| #4 null/undefined | pass | All nullish coalesce; `fn.is_new ?? true` preserves false. |
| #5 module/declarations | pass (50-15 scope) | Canonical `FootnoteData` import; local shadow removed. GameStateProvider/payloads fork on Fact* types is pre-existing — see Delivery Findings. |
| #6 React/JSX | pass | useEffect deps unchanged by diff; no `key={index}`; no `dangerouslySetInnerHTML`. |
| #7 async/promises | n/a | No async in changed lines. |
| #8 test quality | pass | Vacuous assertions removed; mock types match; non-null assertions guarded; no `as any`. |
| #9 build/config | pass | `skipLibCheck: true` is project-wide and pre-existing; not introduced. |
| #10 input validation | pass (50-15 scope) | The cast `msg.payload.footnotes as FootnoteData[]` is pre-existing; the `!fn.fact_id` guard is the new runtime check this story adds. |
| #11 error handling | pass | `console.warn + continue` is loud-skip per SOUL "No Silent Fallbacks." |
| #12 performance/bundle | pass | `readFileSync` in tests is fine in Node test runtime; no barrel imports. |
| #13 fix-introduced regressions | pass | Re-scan after my own edits found no new violations. |

### Project Rules

- **SOUL "No Silent Fallbacks":** Honored — missing fact_id triggers `console.warn` skip; no synthetic fallback re-introduced.
- **SOUL "Every Test Suite Needs a Wiring Test":** Honored — AC5 wiring test (with commented-out negative guard added during review).
- **CLAUDE.md "Verify Wiring, Not Just Existence":** Honored — `useStateMirror` import + call assertions in `App.tsx`.
- **ADR-100 Seam C UI part 1:** Honored — narrator-supplied `fact_id` is now canonical; per-fact dedupe across NARRATION ↔ JOURNAL_RESPONSE.

### Adversarial Probes That Did Not Stick

- Tried to find a footnote shape (mixed marker/no-marker, multi-turn duplicate) the new code would mishandle — covered by AC2 distinct-ids and per-fact-dedupe tests.
- Tried to find a way the synthetic-id regex `/^\d+-\d+$/` would false-positive on a real narrator fact_id — ADR-100 fact_ids are content-derived strings, not pure digit-dash-digit. Acceptable risk.
- Looked for a React-render edge case where `seenFactIds` could leak across replays — the set is rebuilt per useEffect run (line 56 in the original file: `const seenFactIds = new Set<string>()`). Idempotent.

### Final State

- 13/13 tests pass on `useStateMirror-50-15-fact-id.test.tsx`
- `npx tsc --noEmit`: clean
- `npx eslint`: clean on changed files
- Three commits on `feat/50-15-journal-ui-fact-id`:
  - `b114a54` test(50-15) — TEA red phase
  - `3ea079a` feat(50-15) — Dev green phase
  - `8be6ffe` review(50-15) — Reviewer inline fixes

**Handoff:** To The Mad Hatter (SM) for the finish phase (create PR, merge, archive).

## Delivery Findings

No upstream findings at setup time.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No upstream findings during test design.

### Dev (implementation)
- **Improvement** (non-blocking): The `@local/dice-lib` import fails to resolve at vitest runtime in 13+ unrelated test files. Introduced by commit `1e4a425` (refactor(dice): consume @local/dice-lib), not by 50-15. Affects `sidequest-ui/src/dice/**` test paths (workspace symlink or vitest alias missing for the local dice workspace package). *Found by Dev during implementation.*

### Reviewer (review)
- **Improvement** (non-blocking): `FactCategory`, `FactSource`, and `Confidence` exist as two divergent forks — one exported from `sidequest-ui/src/providers/GameStateProvider.tsx` (TitleCase: `'Observation'`, `'Suspected'`, etc., which `useStateMirror.ts` consumes) and another exported from `sidequest-ui/src/types/payloads.ts` (lowercase: `'narrator'`, `'certain'`, etc.). The `as FactSource` and `as Confidence` casts at `useStateMirror.ts:197-198` compile only because the GameStateProvider fork has the literal members; reconciling the two forks would break those casts. Pre-existing; not introduced by 50-15. Affects `sidequest-ui/src/hooks/useStateMirror.ts` and `sidequest-ui/src/types/payloads.ts`. *Found by Reviewer during review.*
- **Improvement** (non-blocking): `useStateMirror.ts:212` carries a pre-existing `msg as unknown as NarrationMessage` double-cast bypass inside the streaming branch. Not introduced by 50-15 and not touched by this diff. Affects `sidequest-ui/src/hooks/useStateMirror.ts:212`. *Found by Reviewer during review.*
- **Gap** (non-blocking): Vitest cannot resolve `@local/dice-lib` on `develop`; 13 dice-related test files and one wiring test fail unrelated to 50-15. Already logged by Dev; restating here to confirm the Reviewer preflight reproduced the failure on `origin/develop`. Affects `sidequest-ui/package.json` (file:../../dice-lib path) and `sidequest-ui/src/dice/**` tests. *Found by Reviewer during review (duplicate of Dev finding).*

## Design Deviations

None at setup time.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Reviewer (review)
- No deviations from spec. Inline fixes applied during review address comment-analyzer and test-analyzer high-confidence findings (drop-path coverage, doc accuracy, vacuous-assertion removal) without altering the AC contract.

### Dev (implementation)
- **Missing fact_id is loud-skip, not synthetic fallback**
  - Spec source: session AC1 + AC2; ADR-100 Seam C feeder description; TEA notes 2
  - Spec text: "Drop synthetic ID generation … fact identity is narrator-supplied only" / "Consume Footnote.fact_id" / "Do not silently re-introduce `${turn}-${marker}`"
  - Implementation: Footnotes arriving without `fact_id` are skipped with `console.warn`. No fallback id is fabricated.
  - Rationale: Server protocol marks `Footnote.fact_id` as `Optional[str]`, but ADR-100 design assumes the narrator emits it. SOUL "No Silent Fallbacks" + TEA's directive to be loud means the right behavior is to drop+warn rather than fabricate. The synthetic-id detector regex in the AC1 test would also fail any `${turn}-${marker}` fallback.
  - Severity: minor
  - Forward impact: minor — if the narrator currently emits any footnotes without fact_id (e.g., legacy prompts), those entries will silently disappear from the player-visible journal until the server prompt is fixed. 50-16 will not regress this; the server prompt for ADR-100 Seam C should already populate fact_id per ADR-039.