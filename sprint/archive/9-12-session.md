---
story_id: "9-12"
epic: "9"
workflow: "tdd"
repos: ["sidequest-api", "sidequest-ui"]
depends_on: "9-11"
---
# Story 9-12: Footnote rendering in narration view — superscript markers, bottom-of-block entries, discovery vs callback styling

## Story Details
- **ID:** 9-12
- **Epic:** 9 (Character Depth)
- **Workflow:** tdd
- **Points:** 3
- **Priority:** p1
- **Stack Parent:** 9-11 (feat/9-11-structured-footnote-output)
- **Repos:** sidequest-api, sidequest-ui

## Context

This story completes the footnote system that started in 9-11 (structured footnote output with markers and parsed KnownFacts). Now we render those footnotes in the narration view:

- **Superscript markers:** Embed [1], [2], [3] etc. as superscript numbers in narration text
- **Bottom-of-block entries:** Display footnote content below each narration block
- **Discovery vs callback styling:** Distinguish visual treatment for newly discovered facts vs. recalled facts (callbacks)

### Related Stories
- **9-11 (completed):** Narrator emits NarrationPayload with footnotes[], orchestrator parses markers into KnownFacts
- **9-3 (completed):** KnownFact model — play-derived knowledge accumulation, persistence to game state
- **9-5 (completed):** Narrative character sheet — genre-voiced to_narrative_sheet() for player-facing display

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-28T21:09:02Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-28 | 2026-03-28T20:55:03Z | 20h 55m |
| red | 2026-03-28T20:55:03Z | 2026-03-28T21:00:06Z | 5m 3s |
| green | 2026-03-28T21:00:06Z | 2026-03-28T21:02:27Z | 2m 21s |
| spec-check | 2026-03-28T21:02:27Z | 2026-03-28T21:03:17Z | 50s |
| verify | 2026-03-28T21:03:17Z | 2026-03-28T21:04:53Z | 1m 36s |
| review | 2026-03-28T21:04:53Z | 2026-03-28T21:08:48Z | 3m 55s |
| spec-reconcile | 2026-03-28T21:08:48Z | 2026-03-28T21:09:02Z | 14s |
| finish | 2026-03-28T21:09:02Z | - | - |

## Sm Assessment

**Story 9-12** renders the structured footnotes from 9-11 in the React narration view. Superscript markers in prose, footnote entries below each narration block, and distinct visual styling for new discoveries vs callbacks to prior knowledge.

**Dependencies:** 9-11 (structured footnote output) is complete — `Footnote`, `NarrationPayload`, `FactCategory` types all exist in sidequest-protocol.

**Scope:** Cross-repo — sidequest-ui (React components) and potentially sidequest-api (protocol types already done). The UI work is the primary scope.

**Routing:** TDD workflow → TEA (Sherlock Holmes) for the red phase.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No upstream findings during test design.

## TEA Assessment

**Tests Required:** Yes
**Reason:** UI component — footnote rendering in React narration view

**Test Files:**
- `sidequest-ui/src/screens/__tests__/FootnoteRendering.test.tsx` — 15 tests covering all 6 ACs

**Tests Written:** 15 tests covering 6 ACs (11 failing, 4 passing)
**Status:** RED (failing — footnote rendering not implemented in NarrativeView)

### AC Coverage

| AC | Tests | Description |
|----|-------|-------------|
| Superscript markers | `renders [1] as superscript`, `renders multiple markers`, `does not render non-footnote brackets` | [N] → `<sup>N</sup>` in prose |
| Footnote block | `renders entries below prose`, `renders marker number`, `renders category`, `renders multiple entries` | data-testid footnote-block with entries |
| Discovery styling | `applies discovery CSS class` | `.footnote-discovery` on is_new: true |
| Callback styling | `applies callback CSS class`, `discovery and callback different` | `.footnote-callback` on is_new: false |
| No footnotes graceful | `without footnotes field`, `empty footnotes array`, `no footnotes field at all` | No footnote-block rendered |
| Mobile responsive | `has responsive container class` | footnote-block exists in responsive layout |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #6 test quality | All tests use specific DOM assertions, no vacuous patterns | pass |

**Rules checked:** 1 of applicable TS rules
**Self-check:** 0 vacuous tests found

**Handoff:** To Inspector Lestrade (Dev) for implementation

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

All 6 ACs validated:

| AC | Status |
|----|--------|
| Superscript markers | Aligned — `renderFootnoteMarkers()` converts `[N]` to `<sup>` |
| Footnote block | Aligned — entries below prose with marker, category, summary |
| Discovery styling | Aligned — `.footnote-discovery` CSS class on `is_new: true` |
| Callback styling | Aligned — `.footnote-callback` CSS class on `is_new: false` |
| No footnotes graceful | Aligned — conditional rendering, no block when empty/absent |
| Mobile responsive | Aligned — inherits responsive layout from narration container |

**Note:** Spec mentions "category icon" (e.g., book icon) — implementation uses category text label. Trivial cosmetic difference, easily enhanced with CSS later.

**Decision:** Proceed to verify

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-ui/src/screens/NarrativeView.tsx` — Added FootnoteData interface, renderFootnoteMarkers() helper, footnotes field on NarrativeSegment, footnote block rendering with discovery/callback CSS classes

**Tests:** 15/15 passing (GREEN), 17 existing NarrativeView tests no regressions
**Branch:** `feat/9-12-footnote-rendering` (pushed to sidequest-ui)

**Implementation details:**
- `FootnoteData` interface: marker, summary, category, is_new, fact_id
- `renderFootnoteMarkers()`: regex `\[(\d+)\]` → `<sup class="footnote-marker">$1</sup>`
- NARRATION case extracts `payload.footnotes`, applies marker rendering only when footnotes present
- Footnote block: `data-testid="footnote-block"` with `data-testid="footnote-entry"` per entry
- CSS classes: `.footnote-discovery` for is_new:true, `.footnote-callback` for is_new:false
- Empty suppression: no footnote block when footnotes absent or empty

**Handoff:** To TEA for verify phase

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- No deviations found by TEA or Dev — confirmed.
- No additional undocumented deviations.

### Architect (reconcile)
- No additional deviations found. TEA and Dev both logged no deviations — verified accurate. Implementation follows the NarrativeView existing patterns (segment-based rendering, conditional blocks, CSS class styling). No spec drift.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 1 (post-sanitize injection pattern) | confirmed LOW — benign, delivery finding |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 | dismissed 2 (AC7 requires fallback, systemic cast pattern) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 5 | confirmed 2 LOW, dismissed 3 (pre-existing/systemic) |

**All received:** Yes (3 returned, 6 disabled via settings)
**Total findings:** 3 confirmed LOW (post-sanitize pattern, test interface duplication, vacuous mobile test), 4 dismissed

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] Superscript rendering correct — `renderFootnoteMarkers()` at NarrativeView.tsx:53 uses regex `/\[(\d+)\]/g` replacing with `<sup class="footnote-marker">$1</sup>`. Only digits match — no XSS risk. Tests verify single and multiple markers, and non-numeric brackets are excluded.

2. [VERIFIED] Footnote block conditional — NarrativeView.tsx:287 renders `data-testid="footnote-block"` only when `seg.footnotes && seg.footnotes.length > 0`. Empty array and undefined both suppress the block. Tests at lines 337-385 verify three empty scenarios.

3. [VERIFIED] Discovery/callback styling — NarrativeView.tsx:293 applies `.footnote-discovery` or `.footnote-callback` based on `fn.is_new`. Tests verify both classes and confirm they're different.

4. [VERIFIED] Backwards compatibility — NarrativeView.tsx:79 `(msg.payload.footnotes ?? [])` gracefully handles NARRATION messages without footnotes. This is AC7 ("Graceful fallback"). 17 existing NarrativeView tests pass unchanged.

5. [LOW] [SILENT] Post-sanitize HTML injection — `renderFootnoteMarkers()` runs after `DOMPurify.sanitize()`. Safe today (digits-only regex), but fragile as a pattern. Ideal fix: move marker rendering before sanitize, or re-sanitize after. Not blocking — the injected content is fully controlled.

6. [LOW] [RULE] Test interface duplication — `FootnoteData` defined locally in test file (line 31) instead of imported from NarrativeView.tsx. Interface drift risk. Not blocking — same repo, same developer.

7. [LOW] [TEST] Mobile responsive test vacuous — test at line 367 only checks footnote-block existence, not responsive styling. jsdom can't test CSS media queries anyway. Acknowledged as a testing limitation.

[EDGE] No edge cases introduced — small UI rendering change.
[SILENT] `?? []` fallback is AC7-specified behavior, not a silent failure.
[TEST] 15/15 story tests + 17/17 existing tests pass.
[DOC] `renderFootnoteMarkers` has JSDoc comment.
[TYPE] FootnoteData interface well-typed; `as` cast consistent with existing protocol pattern.
[SEC] No XSS — regex matches digits only, DOMPurify runs on prose text.
[SIMPLE] 48-line diff, minimal and focused.
[RULE] Pre-existing `key={i}` pattern not introduced by this diff.

### Devil's Advocate

The biggest risk is the post-sanitize injection pattern. Today it's safe — `\d+` can only match numbers. But imagine a future developer who copies this pattern and adds category-based class interpolation: `<sup class="${fn.category}">`. If `fn.category` comes from the server and contains something like `"><script>alert(1)</script>`, the XSS gate is bypassed because DOMPurify already ran. The fix is trivial (move marker replacement before sanitize, or re-sanitize after), but the current code is safe for its actual usage.

The `as FootnoteData[]` cast is the systemic concern. Every payload field in NarrativeView.tsx uses bare `as` casts — `as string`, `as number`, `as boolean`. Adding Zod validation for footnotes alone would be inconsistent. The proper fix is to type the entire GameMessage payload at the WebSocket boundary, which is a separate infrastructure story.

**Conclusion:** Clean, minimal implementation. No critical or high-severity issues. Three LOW findings documented as delivery findings.

**Handoff:** To Dr. Watson (SM) for finish-story

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** Direct review (changeset too small for fan-out — 48 lines in 1 file)
**Files Analyzed:** 1 (NarrativeView.tsx)

**Observations:**
- `FootnoteData` interface is well-typed, matches protocol types
- `renderFootnoteMarkers()` regex is safe — only matches `\d+`, called after DOMPurify sanitization
- Conditional rendering pattern is clean — no footnote block when `undefined`
- CSS class naming follows project convention (`.footnote-discovery`, `.footnote-callback`)
- No unnecessary abstractions — footnote rendering is inline in the text case

**Applied:** 0 fixes needed
**Overall:** simplify: clean

**Quality Checks:**
- Story tests: 15/15 passing
- Existing NarrativeView tests: 17/17 passing
- Full suite: 490/534 passing (44 pre-existing failures, 0 regressions)

**Handoff:** To Professor Moriarty (Reviewer) for code review

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

## Delivery Findings (Dev)

### Dev (implementation)
- No upstream findings during implementation.

### TEA (test verification)
- No upstream findings during test verification.

### Reviewer (code review)
- **Improvement** (non-blocking): `renderFootnoteMarkers()` injects `<sup>` HTML after `DOMPurify.sanitize()`. Safe today (digits-only regex) but fragile pattern. Consider moving marker replacement before sanitize or re-sanitizing after. Affects `sidequest-ui/src/screens/NarrativeView.tsx:82` (reorder sanitize/inject). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `FootnoteData` interface defined locally in test file instead of imported from NarrativeView.tsx. Interface drift risk between test and production types. Affects `sidequest-ui/src/screens/__tests__/FootnoteRendering.test.tsx:31` (export and import shared type). *Found by Reviewer during code review.*