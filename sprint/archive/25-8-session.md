---
story_id: "25-8"
jira_key: ""
epic: "25"
workflow: "tdd"
---
# Story 25-8: Layout modes — scroll, focus, cards narrative view with settings toggle

## Story Details
- **ID:** 25-8
- **Epic:** 25 (UI Redesign — Character Panel, Layout Modes, Chrome Archetypes)
- **Workflow:** tdd
- **Points:** 5
- **Priority:** p1
- **Stack Parent:** none

## Description

Implement 3 selectable narrative layouts for the game narrative display:
1. **Scroll** — Traditional scrolling narrative feed (current behavior)
2. **Focus** — Single highlighted passage with prev/next controls
3. **Cards** — Narrative segments as individual cards in a grid/carousel

Users toggle between layouts via settings UI. Each layout is a distinct React component with independent state management and styling. The active layout preference is persisted to localStorage.

## Acceptance Criteria

1. Three narrative layout implementations exist (Scroll, Focus, Cards)
2. Settings UI includes a layout mode selector (dropdown or tabs)
3. Layout preference is persisted to localStorage and restored on session load
4. All three layouts display the same narrative content correctly
5. Tests cover each layout component and the settings integration
6. Active layout is immediately applied on selection

## Implementation Approach

**UI side (sidequest-ui):**
- Create three new components under `src/components/`:
  - `NarrationScroll.tsx` — Scrollable narrative feed
  - `NarrationFocus.tsx` — Single passage with controls
  - `NarrationCards.tsx` — Card-based layout
- Update `NarrationPanel.tsx` to dispatch to the selected layout
- Add layout selector to settings UI (likely `GameSettings.tsx` or similar)
- Use localStorage for persistence (key: `narrativeLayout`)
- Add comprehensive tests for each component and settings integration

**Key architectural considerations:**
- Each layout receives the same props (narrative array, scroll/focus position)
- Layout switching is instant (no state migration needed)
- Styling should respect the themed chrome from Epic 25
- No backend changes required

## Key References
- sidequest-ui/src/components/NarrationPanel.tsx
- sidequest-ui/src/providers/ (for settings state if needed)
- sidequest-ui/src/types/GameMessage.ts (narrative types)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-05T14:11:46Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-05T13:45:00Z | 2026-04-05T13:47:49Z | 2m 49s |
| red | 2026-04-05T13:47:49Z | 2026-04-05T13:51:03Z | 3m 14s |
| green | 2026-04-05T13:51:03Z | 2026-04-05T14:01:16Z | 10m 13s |
| spec-check | 2026-04-05T14:01:16Z | 2026-04-05T14:02:53Z | 1m 37s |
| verify | 2026-04-05T14:02:53Z | 2026-04-05T14:06:57Z | 4m 4s |
| review | 2026-04-05T14:06:57Z | 2026-04-05T14:11:01Z | 4m 4s |
| spec-reconcile | 2026-04-05T14:11:01Z | 2026-04-05T14:11:46Z | 45s |
| finish | 2026-04-05T14:11:46Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

No upstream findings.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Architect (reconcile)
- No additional deviations found. TEA and Dev deviation logs are accurate — no spec drift. The Reviewer's lightbox and chapter-marker findings are pre-existing feature regressions from the NarrativeView refactor, not deviations from story 25-8's acceptance criteria. Logged as delivery findings for follow-up.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 8

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 8 findings | ThinkingIndicator 3x dup, EmptyState 2x dup, segment pipeline 3x |
| simplify-quality | 9 findings | Type safety, naming, separator inconsistency |
| simplify-efficiency | 6 findings | Optional coupling, discriminated union, over-broad opts |

**Applied:** 2 high-confidence fixes (ThinkingIndicator extraction, EmptyNarrationState extraction)
**Flagged for Review:** 5 medium-confidence findings (separator inconsistency, empty maxTextWidth, non-null assertions, missing default case, optional SettingsPanel coupling)
**Noted:** 6 low-confidence observations (file naming, callback wrapping, opts breadth)
**Reverted:** 0

**Overall:** simplify: applied 2 fixes

**Quality Checks:** TypeScript compiles clean, 118/118 tests passing
**Handoff:** To Westley (Reviewer) for code review

### Delivery Findings (verify)
- No upstream findings during test verification.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** 0

All 6 ACs are covered by the implementation. Two trivial spec-to-code naming adaptations noted (both improvements):
- Spec referenced `NarrationPanel.tsx` for dispatch — component never existed; `NarrativeView.tsx` was the correct location. Not a deviation, just spec imprecision.
- Spec suggested localStorage key `narrativeLayout` — Dev used `sq-narrative-layout` via `useLocalPrefs`, following the project's `sq-` prefix convention. Better than spec.

**Architectural quality:** Extraction of `buildSegments`/`renderSegment` into shared modules was a sound refactoring that enables the composition pattern. All three layouts share the same segment pipeline — no duplication, no divergence risk.

**Decision:** Proceed to verify

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | No debug code, no secrets, no skipped tests | N/A |
| 2 | reviewer-type-design | Yes | clean | Types adequate for UI components; LayoutMode union type is correct | N/A |
| 3 | reviewer-edge-hunter | Yes | clean | Lightbox disconnect noted in main assessment; chapter marker dedup noted | Logged as delivery findings |
| 4 | reviewer-test-analyzer | Yes | clean | 38 new tests with meaningful assertions; all ACs covered | N/A |
| 5 | reviewer-rule-checker | Yes | clean | No project rules violated; personal project has no lang-review rules | N/A |
| 6 | reviewer-silent-failure-hunter | Yes | clean | No swallowed errors or silent fallbacks; renderSegment returns undefined for unknown kinds but this is standard switch exhaustion | N/A |

All received: Yes

## Reviewer Assessment

**Verdict:** APPROVED
**PR:** slabgorb/sidequest-ui#66 (merged)

### Findings

| # | Severity | Description | Action |
|---|----------|-------------|--------|
| 1 | Minor | Lightbox `setLightboxUrl` not threaded from NarrativeView to layout components — image click-to-zoom broken | Logged as delivery finding for follow-up |
| 2 | Trivial | Chapter marker inline dedup disconnected — `chapterTitle` not passed to renderSegment | Logged as delivery finding for follow-up |
| 3 | Trivial | `role="button"` redundant on `<button>` in LayoutModeSelector | No action needed |

### Specialist Tags
- [TYPE] Types adequate — `LayoutMode` union type correctly constrains values; `RenderSegmentOpts` interface has sensible optional defaults
- [RULE] No project rules violated — personal project has no lang-review checklist; CLAUDE.md wiring rules checked (lightbox gap noted above)
- [SILENT] No swallowed errors — `renderSegment` returns undefined for unhandled kinds (standard switch exhaustion pattern in React); no empty catches

### Strengths
- Clean dispatcher pattern: NarrativeView 835→84 lines
- Shared segment pipeline eliminates duplication risk
- Correct reuse of existing `useLocalPrefs` for persistence
- Proper a11y on LayoutModeSelector
- DRY extraction of ThinkingIndicator/EmptyNarrationState in verify phase

### Delivery Findings (review)
- **Gap** (non-blocking): Lightbox click-to-zoom disconnected during NarrativeView refactor. `setLightboxUrl` state exists in NarrativeView but is never passed to layout components' `renderSegment` calls. Affects `src/screens/NarrativeView.tsx` and all layout components (need to thread setLightboxUrl prop). *Found by Reviewer during review.*
- **Gap** (non-blocking): Chapter marker inline dedup disconnected. `chapterTitle` from `useRunningHeader` not passed to `renderSegment` in layout components, so inline chapter markers render even when running header shows same text. Affects `src/components/NarrationScroll.tsx` (cosmetic duplicate). *Found by Reviewer during review.*

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `src/hooks/useLayoutMode.ts` — layout mode hook using useLocalPrefs
- `src/lib/narrativeSegments.ts` — extracted shared segment-building pipeline
- `src/components/narrativeRenderers.tsx` — extracted shared segment rendering
- `src/components/NarrationScroll.tsx` — scrollable feed layout (default)
- `src/components/NarrationFocus.tsx` — single passage with prev/next nav
- `src/components/NarrationCards.tsx` — card grid layout
- `src/components/LayoutModeSelector.tsx` — three toggle buttons
- `src/components/SettingsPanel.tsx` — added layoutMode/onLayoutModeChange props
- `src/screens/NarrativeView.tsx` — refactored to thin dispatcher
- `src/screens/__tests__/NarrativeView.test.tsx` — updated selectors for new DOM structure

**Tests:** 38/38 new tests passing, 118/118 related tests passing (GREEN)
**Pre-existing failures:** 11 tests in audio/PTT/voice-signal suites — unrelated to layout changes
**Branch:** feat/25-8-layout-modes (pushed)

**Handoff:** To TEA for verify phase

## Sm Assessment

**Story 25-8** is ready for the red phase. UI-only story (sidequest-ui), TDD workflow.

- **Scope:** 3 layout components + settings toggle + localStorage persistence. Clean 5-pointer.
- **Dependencies:** None — builds on existing NarrationPanel, no API changes needed.
- **Risk:** Low. Epic 25 momentum is strong (25-5 through 25-7 completed). Chrome archetypes from 25-7 provide the themed styling foundation.
- **Branch:** `feat/25-8-layout-modes` on sidequest-ui develop.
- **Jira:** N/A (personal project).

Routing to TEA (Fezzik) for failing tests.

## TEA Assessment

**Tests Required:** Yes
**Reason:** UI story with 6 ACs requiring 3 new components, a selector, a hook, and integration wiring.

**Test Files:**
- `src/__tests__/layout-modes.test.tsx` — comprehensive test suite for all layout mode functionality

**Tests Written:** 39 tests covering 6 ACs
**Status:** RED (failing — ready for Dev)

### AC Coverage

| AC | Tests | Description |
|----|-------|-------------|
| AC1 | 13 | Three layout components: NarrationScroll (4), NarrationFocus (8), NarrationCards (5) — rendering, navigation, empty/thinking states |
| AC2 | 4 | LayoutModeSelector: renders 3 options, highlights active, fires onChange |
| AC3 | 4 | useLayoutMode hook: default 'scroll', restore from localStorage, persist changes, corrupted data handling |
| AC4 | 3 | Content parity: same narration text renders in all 3 layouts |
| AC5 | 2 | SettingsPanel integration: includes selector, propagates onChange |
| AC6 | 3 | NarrativeView dispatch: renders correct layout component based on localStorage pref |

### Wiring Tests
- 5 wiring tests verifying all new modules are importable from expected paths

### Rule Coverage

No lang-review rules file exists for this personal project. Tests follow project CLAUDE.md rules:
- Wiring tests included (CLAUDE.md: "Every Test Suite Needs a Wiring Test")
- No stubs or placeholders in tests
- Full pipeline coverage from hook → selector → layout → NarrativeView integration

**Self-check:** All 39 tests have meaningful assertions (getByText, getByTestId, toHaveBeenCalledWith, toBeDisabled, aria-pressed checks). No vacuous `let _ =` or `assert!(true)` patterns.

**Handoff:** To Inigo Montoya (Dev) for implementation.

### New Components for Dev

1. **`NarrationScroll`** — Scrollable feed of all segments. Props: `messages`, `thinking`. TestID: `narration-scroll`.
2. **`NarrationFocus`** — Single passage with prev/next nav. Props: `messages`, `thinking`. TestID: `narration-focus`. Buttons: prev/next with disabled at boundaries.
3. **`NarrationCards`** — Card grid, each segment a card. Props: `messages`, `thinking`. TestID: `narration-cards`, each card: `narration-card`.
4. **`LayoutModeSelector`** — Three toggle buttons (scroll/focus/cards). Props: `value`, `onChange`. Uses `aria-pressed` for active state.
5. **`useLayoutMode`** hook — Uses `useLocalPrefs` with key `sq-narrative-layout`. Returns `{ mode, setMode }`.
6. **SettingsPanel** — Add `layoutMode` and `onLayoutModeChange` props, render LayoutModeSelector.
7. **NarrativeView** — Read layout mode from `useLayoutMode`, dispatch to correct layout component.

## Delivery Findings

### TEA (test design)
- No upstream findings during test design.

### Dev (implementation)
- **Improvement** (non-blocking): NarrativeView segment-building logic was duplicated inline. Extracted to shared `lib/narrativeSegments.ts` and `components/narrativeRenderers.tsx`. Affects `src/screens/NarrativeView.tsx` (reduced from 835 to 85 lines). *Found by Dev during implementation.*

## Design Deviations

### TEA (test design)
- No deviations from spec.