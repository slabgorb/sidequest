---
story_id: "73-14"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 73-14: BeatImpactPanel you/them labels + signed numeric deltas

## Story Details
- **ID:** 73-14
- **Jira Key:** (none — Jira not enabled)
- **Workflow:** tdd
- **Points:** 2
- **Stack Parent:** none
- **Repo:** sidequest-ui

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-05T06:01:34Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-05T03:17:08Z | 2026-06-05T03:18:48Z | 1m 40s |
| red | 2026-06-05T03:18:48Z | 2026-06-05T03:35:32Z | 16m 44s |
| green | 2026-06-05T03:35:32Z | 2026-06-05T03:40:29Z | 4m 57s |
| review | 2026-06-05T03:40:29Z | 2026-06-05T06:01:34Z | 2h 21m |
| finish | 2026-06-05T06:01:34Z | - | - |

## Sm Assessment

Setup verified by SM (Morpheus). Story 73-14 is a well-scoped 2-point, purely presentational UI change to BeatImpactPanel in sidequest-ui — no API/state surface. The single load-bearing risk is the four existing test files (from 73-4/73-7/73-9 plus 73-10's CSS work) that assert numeric content against this render: adding "you"/"them" labels and +/- sign prefixes will shift the rendered text, so TEA must inventory those assertions in RED and decide per-test whether the new content satisfies them or the assertions need updating (with justification). CSS scaffolding already landed in 73-10, so this is label/sign text only. Player-facing legibility for Sebastien/Jade (mechanics-first). Routing to TEA for the RED phase.

## Delivery Findings

No upstream findings.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): Dev should reuse the existing `SIDE_LABEL = {player:"You", opponent:"Them"}` constant (ConfrontationOverlay.tsx:301) for the labels and mirror the `LedgerRow` sign idiom (`delta > 0 ? `+${delta}` : `${delta}``, ConfrontationOverlay.tsx:617-618) for the sign, rather than introducing a parallel label/sign helper. Affects `sidequest-ui/src/components/ConfrontationOverlay.tsx` (BeatImpactPanel render, lines ~786-795). *Found by TEA during test design.*

## Impact Summary

**Upstream Effects:** 1 findings (0 Gap, 0 Conflict, 0 Question, 1 Improvement)
**Blocking:** None

- **Improvement:** Dev should reuse the existing `SIDE_LABEL = {player:"You", opponent:"Them"}` constant (ConfrontationOverlay.tsx:301) for the labels and mirror the `LedgerRow` sign idiom (`delta > 0 ? `+${delta}` : `${delta}``, ConfrontationOverlay.tsx:617-618) for the sign, rather than introducing a parallel label/sign helper. Affects `sidequest-ui/src/components/ConfrontationOverlay.tsx`.

### Downstream Effects

- **`sidequest-ui/src/components`** — 1 finding

## TEA Assessment

**Tests Required:** Yes
**Reason:** Player-facing render behavior with three concrete ACs (you label, them label, signed deltas).

**Test Files:**
- `sidequest-ui/src/components/__tests__/ConfrontationOverlay.beatimpactlabels.test.tsx` — 8 tests across labels, signed deltas, and a 73-7-contract-preservation guard.

**Tests Written:** 8 tests covering 3 ACs (you/them labels, signed positive/negative/zero deltas) + the preserved 73-7 numeric contract.
**Status:** RED — 4 failing (the new behavior), 4 passing (guard/characterization tests that must REMAIN true).

**RED evidence (vitest, 5 files run):** `Test Files 1 failed | 4 passed (5) · Tests 4 failed | 21 passed (25)`.
- The 4 failures are the genuinely-new behavior: `you` label, `them` label, `+3` own sign, `+2` opponent sign.
- The 4 new-file passes are guards (side-correct labels, negative `-2` ASCII sign, zero `0` not dropped, digit-preservation/no-cross-contamination) — they pin behavior that must stay true post-implementation.
- **The four "at-risk" existing files all stayed GREEN** (17/17): 73-4 (`beatimpact`), 73-7 (`opponentbeatimpact`), 73-9 (`coverage`), 73-10 (`beatimpactstyling`). The SM-flagged regression risk did **not** materialize — those suites assert delta digits via *substring* `toHaveTextContent('3'|'2'|'0')` and 73-10 asserts only CSS/attributes; the label words carry no digits, so labels+signs coexist without breaking them.

**Pinned DOM contract (for Dev):**
- Label travels INSIDE the existing readout span — `beat-impact-own` contains a /you/i label, `beat-impact-opponent` contains a /them/i label (case-insensitive, so reusing `SIDE_LABEL`'s "You"/"Them" satisfies them).
- Sign is ASCII `+`/`-` (matches `LedgerRow`), not a Unicode minus.
- Positive → leading `+`; negative → natural `-`; zero → bare `0` (sign guard is `delta > 0`, NOT `>= 0`); the 73-7 numeric digit still renders in each span.

### Rule Coverage

| Rule (typescript lang-review) | Test | Status |
|------|------|--------|
| #4 null/undefined — `own` can be `0` (valid, not a fallback); guard must not coalesce it away | `renders a zero own delta as the digit 0 (valid value, not dropped)` | passing (guard) |
| #8 test quality — meaningful assertions, no `as any` | self-checked all 8 tests | passing |

**Rules checked:** 2 of 13 lang-review rules apply to this cosmetic UI change (the rest — async, enums, modules, input-validation, etc. — are N/A for a label/sign render).
**Self-check:** 0 vacuous tests found. Every test has a concrete substring/regex assertion; no `let _ =`, no `assert(true)`, no always-None checks.

**Handoff:** To Dev (Agent Smith) for GREEN.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings during implementation. TEA's contract was precise and complete; the existing `SIDE_LABEL` / `LedgerRow` precedents made this a near-mechanical change with no surprises.

### Reviewer (code review)
- No upstream findings against the 73-14 code itself. The diff is surgical, both enabled subagents returned clean, and the existing `.beat-impact` flex container already provides the inter-span spacing the new labels need.
- **Gap** (blocking — sprint-data, NOT 73-14 code): `pf sprint story update 73-14 --review-verdict approved` was rolled back by a whole-sprint validation failure unrelated to this story — `84-1.depends_on` references non-existent story `76-7`. Consequently `73-14.review_verdict` is still `null`, and **`pf sprint story finish 73-14` will hit the same validation error** until `84-1` is fixed. Affects `sprint/current-sprint.yaml` (`84-1.depends_on`: point it at an existing story or remove it; then re-run the verdict update / finish). *Found by Reviewer during code review.* The 73-14 review verdict is APPROVED regardless — see Reviewer Assessment.

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec. The story context left ACs to TEA ("TEA to define during the RED phase"); the three ACs I pinned (you/them labels, signed deltas) derive directly from the story title and are tested as written. Zero-delta sign behavior (`0` renders unsigned) follows the existing `LedgerRow` precedent in the same file rather than inventing a `+0`/`±0` convention — a defined AC, not a deviation.

### Dev (implementation)
- No deviations from spec. Implemented exactly to TEA's pinned DOM contract: labels reuse `SIDE_LABEL` ("You"/"Them") inside the existing readout spans, sign uses the shared `formatSignedDelta` helper (positive `+N`, negative ASCII `-N`, zero bare `0` via a `> 0` guard). The only adjacent-code touch was extracting `formatSignedDelta` from `LedgerRow`'s identical inline expression into a shared module-level helper and pointing `LedgerRow` at it — a behavior-preserving DRY consolidation that follows TEA's non-blocking Improvement note, not a spec deviation (LedgerRow output is byte-identical; all 1908 tests pass).

### Reviewer (audit)
- **TEA "No deviations from spec" (zero-delta renders unsigned)** → ✓ ACCEPTED by Reviewer: pinning `0`→bare `"0"` to the existing `LedgerRow` precedent is sound and consistent; defining an open AC is not a deviation.
- **Dev "No deviations from spec" (shared `formatSignedDelta` extraction)** → ✓ ACCEPTED by Reviewer: the extraction is behavior-preserving (LedgerRow output byte-identical, verified by the green full suite) and removes a real duplication TEA flagged — a net quality improvement, not a divergence.
- No undocumented deviations found. Spec (AC1–AC6) maps exactly to the implementation; nothing diverged silently.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-ui/src/components/ConfrontationOverlay.tsx` — (1) added shared `formatSignedDelta(delta)` helper next to `SIDE_LABEL`; (2) pointed `LedgerRow` at it (removed duplicated inline sign expression); (3) `BeatImpactPanel` readout spans now render `{SIDE_LABEL.player} {formatSignedDelta(...)}` and `{SIDE_LABEL.opponent} {formatSignedDelta(...)}` instead of the bare `{own ?? 0}` integers.

**Tests:** 25/25 passing on the new + four at-risk files; **1908/1908 full suite (199 files)** GREEN. Lint clean (eslint exit 0), typecheck clean (`tsc --noEmit` exit 0).
**Branch:** feat/73-14-beatimpactpanel-you-them-labels (pushed, tracking origin)

**AC verification:**
- AC1/AC2 — "You"/"Them" labels travel inside `beat-impact-own`/`beat-impact-opponent` (reused `SIDE_LABEL`). ✅
- AC3 — explicit sign: `+3`/`+2` positives, ASCII `-2` negatives, bare `0` for zero (guard `> 0`). ✅
- AC4 — layout: labels/signs are plain inline text inside the existing `.text-xs` spans; 73-10 CSS (`data-effect` border/glyph) untouched and its suite stays GREEN. ✅
- AC5 — no assertion rewrites needed: all four at-risk suites (73-4/73-7/73-9/73-10) pass unchanged. ✅
- AC6 — own vs opponent now disambiguated by visible label + sign, not just DOM testid. ✅

**No OTEL needed:** cosmetic UI change (labels/text only) — per sidequest-ui CLAUDE.md, OTEL is "not needed for cosmetic UI changes (labels, spacing, colors)."

**Handoff:** To Reviewer (The Merovingian) for the review phase.

**Story Context:**
This story adds player-facing legibility to the BeatImpactPanel numeric display by disambiguating dial-delta values. Two adjacent bare integers (own change + opponent change) currently require testid inspection to understand which is which. This fix adds:
- Text labels: "you" and "them" flanking the two deltas
- Numeric sign prefix: explicit +/- before each number

**Dependencies:**
- Deferred from 73-7 (Architect/Reviewer notes) and 73-10 (Dev)
- 73-4/73-7/73-9 assert numeric content against the BeatImpactPanel render
- CSS styling already shipped in 73-10 (ready to receive the label/sign updates)

**Audience:**
- Primary: Sebastien and Jade (mechanics-first players who want to see the math)
- Secondary: anyone reading the dial-impact summary in player-facing surfaces

**Technical Surface:**
- BeatImpactPanel React component (src/components/)
- Test coverage: 4 existing test files assert numeric content; changes must preserve test contracts or update assertions in coordination with test reviewers
- No API/state changes — purely presentational

## Acceptance Criteria

1. BeatImpactPanel displays "you" label before the own-dial delta number
2. BeatImpactPanel displays "them" label before the opponent-dial delta number
3. Both numeric deltas include explicit +/- sign prefix (e.g., "+2", "-1")
4. Layout remains visually balanced (CSS from 73-10 applies correctly)
5. All existing tests in the 4 test files pass (or assertions updated with justification in the PR description)
6. Player can clearly distinguish "my change" from "opponent change" at a glance

## Branch Strategy
**Strategy:** gitflow (feat/73-14-beatimpactpanel-you-them-labels)

## Subagent Results

Per `workflow.reviewer_subagents` settings, only `preflight` and `security` are enabled; the other seven are disabled and pre-filled as Skipped. I covered each disabled subagent's domain myself against this small, single-file cosmetic diff (see tagged observations in the assessment).

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | success | none (1908/1908 tests, lint clean, tsc clean, 0 smells) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (2 enabled returned, both clean; 7 disabled via settings)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** Server `CONFRONTATION` payload → `BeatImpactView.own: number | undefined` → `impact.own ?? 0` (ConfrontationOverlay.tsx:802) → `formatSignedDelta(delta: number)` (line 309) → JSX text node inside `<span data-testid="beat-impact-own">`. Safe because: (1) `own` is type-constrained to `number`; a number's `.toString()` cannot carry HTML-significant characters; (2) the value is a React text node (`createTextNode`), not `dangerouslySetInnerHTML`, so it is auto-escaped even if the wire value were malformed; (3) `SIDE_LABEL.player/.opponent` are static module-level constants, not attacker-controlled. `[SEC]` confirms clean.

**Pattern observed:** Shared-helper extraction to prevent drift — `formatSignedDelta` (line 309) is now the single source of the sign idiom for both `LedgerRow` (line 625) and `BeatImpactPanel` (lines 802, 807). This is the DRY consolidation TEA's Improvement note requested; it removes a duplicated inline ternary rather than adding a second one.

**Error handling:** `impact.own ?? 0` and `opponent.own ?? 0` (lines 802/807) use nullish coalescing (not `||`), so a legitimate `0` delta is preserved and rendered, while `undefined` falls back to `0`. The readout spans remain gated on `impact != null` / `opponent != null` (unchanged from 73-13), so the opponent-acts-first window still omits the absent half rather than rendering a misleading value.

### Observations (subagent findings tagged by source; disabled domains covered by Reviewer)

- `[VERIFIED]` Sign logic correct — `formatSignedDelta` line 309: `delta > 0 ? `+${delta}` : `${delta}``. `3`→`"+3"`, `-2`→`"-2"`, `0`→`"0"`. Guard is `> 0` (not `>= 0`), so zero reads as a bare `0`, not a phantom `+0`. Complies with lang-review #4 (0 is a valid value, must not be coalesced/signed away).
- `[VERIFIED]` Nullish coalescing — lines 802/807 use `??`, never `||`; evidence: `BeatImpactView.own?: number` (line 111) means `undefined` is the only falsy-but-absent case, and `0` is a valid delta that must survive. lang-review #4 compliant.
- `[VERIFIED]` Side-correct mapping — own span uses `SIDE_LABEL.player` ("You"), opponent span uses `SIDE_LABEL.opponent` ("Them"); no swap. Test `keeps the labels side-correct` guards this.
- `[VERIFIED]` Layout not jammed — `.beat-impact` is `display:flex; align-items:baseline; gap:0.4rem` (beat-impact.css:18-24), so `[glyph]·[summary]·[You +3]·[Them +2]` render with a 0.4rem gap between flex items. AC4 ("visually balanced") is satisfied by the existing container; no new CSS needed. The `data-effect` ::before glyph rules (73-10) are untouched.
- `[SEC]` reviewer-security → clean. No `dangerouslySetInnerHTML`, no `JSON.parse … as T`, no unescaped interpolation; the only server value (`own: number`) renders as an escaped text node. No injection / info-leak path. Confirmed, no action.
- `[SIMPLE]` (subagent disabled) — Reviewer pass: the change *reduces* complexity (one shared helper replaces a duplicated ternary). 6-line module helper + 2 call sites; no dead code, no over-engineering. Clean.
- `[TEST]` (subagent disabled) — Reviewer pass: 8 tests, all with concrete substring/regex assertions (no vacuous `assert(true)`, no `as any`). Coverage spans both ACs (labels + signs), the negative and zero edges, side-correctness, and a 73-7 contract-preservation guard. The negative-sign test even pins ASCII `-2` to forbid a Unicode-minus regression. Strong.
- `[TYPE]` (subagent disabled) — Reviewer pass: `formatSignedDelta(delta: number): string` is fully typed; no `any`, no unsafe cast, no stringly-typed API. `SIDE_LABEL` is `Record<MetricSide, string>`. tsc clean (preflight). No type-design issue.
- `[EDGE]` (subagent disabled) — Reviewer pass: boundary values enumerated — positive (`+3`), negative (`-2`), zero (`0`), and `undefined`→`0` (via `??`). NaN/Infinity are unreachable for an integer dial delta from the server and were not introduced by this change. No unhandled path.
- `[SILENT]` (subagent disabled) — Reviewer pass: no try/catch, no swallowed errors, no silent fallback introduced. The `?? 0` is an explicit, documented default for an absent optional, not an error-masking fallback. Clean.
- `[DOC]` (subagent disabled) — Reviewer pass: the new helper carries an accurate inline comment explaining the `> 0` zero-guard rationale; the BeatImpactPanel comment correctly attributes the change to 73-14 and explains the disambiguation intent. No stale/misleading comments. `[RULE]` (subagent disabled) — Reviewer pass: applicable lang-review rules (#4 nullish, #6 react/jsx no dangerous HTML, #8 test quality) all pass; no rule violations.

### Rule Compliance (lang-review/typescript — applicable rules enumerated)

- **#4 Null/undefined** — `impact.own ?? 0`, `opponent.own ?? 0` (lines 802/807): `??` used, not `||`; `0` is a valid value and is preserved. **Compliant** (every nullable read in the diff checked).
- **#6 React/JSX** — no `dangerouslySetInnerHTML`; no `useEffect`/hooks added; no `key={index}`; values render as escaped text nodes. **Compliant** (every JSX expression in the diff checked).
- **#8 Test quality** — no `as any` in the test file; assertions are meaningful substring/regex checks; mock data matches `ConfrontationData`/`BeatImpactView` types. **Compliant** (all 8 tests checked).
- **#1 Type-safety escapes / #3 enums / #10 input validation / #11 error handling** — no instances in the diff (no casts, no enums added, no API boundary, no catch). **N/A — nothing to check.**

### Devil's Advocate

Let me argue this code is broken. *The labels are jammed against the numbers and against the summary, so "You +3Them +2" is illegible* — refuted: `.beat-impact` is a flex row with `gap:0.4rem` (beat-impact.css:19-21), so each readout is a separated flex item; the rendered run is `[✓] [summary] [You +3] [Them +2]` with real spacing. *A malicious server sends `own: "<img onerror=...>"` to inject script* — refuted: the value is rendered as a React text node, auto-escaped; even a type-violating string cannot become markup, and `[SEC]` confirmed it. *A confused user reads `+0` and thinks the beat helped* — refuted: the `> 0` guard renders zero as a bare `0`, and 73-10's `inert` styling (faded, `–` glyph) already signals "no move"; the test pins the bare `0`. *A float delta like `2.5` would render `+2.5` and break the integer assumption* — the server's dial deltas are integers (`base`/tier defaults are ints), and even if a float arrived, `+2.5` is still a correct, legible signed string — no crash, no misread. *The `formatSignedDelta` extraction silently changed `LedgerRow`'s output* — refuted: the new expression is byte-identical to the prior inline ternary, and the full 1908-test suite (including LedgerRow-exercising suites) stayed green. *A negative zero `-0` would render `"0"`?* — `-0 > 0` is false, so `${-0}` → `"0"`; correct, no `"-0"` leak. *Screen-reader users lose context* — actually improved: the old bare `3` is now the self-describing `"You +3"`. I find no break. The change is additive, type-safe, well-tested, and the one layout risk is neutralized by the pre-existing flex container.

**Wiring:** `BeatImpactPanel` is rendered by `ConfrontationOverlay` (the component the tests mount end-to-end), which is the live confrontation surface in the game client. The new labels/signs are reachable from the production render path, not an isolated unit. `SIDE_LABEL` and `formatSignedDelta` are both consumed by non-test production code. Confirmed wired.

**Verdict rationale:** No Critical/High issues. Both enabled subagents clean. 11 observations recorded (4 VERIFIED + 7 domain passes/confirmations), exceeding the 5-minimum, with zero blockers. All six ACs met and independently verified. The change is the smallest correct diff for the story and even pays down a duplication TEA flagged.

**Handoff:** To SM (Morpheus) for finish-story.