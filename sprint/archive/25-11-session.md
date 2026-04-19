---
story_id: "25-11"
jira_key: "none"
epic: "25"
workflow: "tdd"
---
# Story 25-11: Wire GameLayout to pass resources and genreSlug to CharacterPanel

## Story Details
- **ID:** 25-11
- **Title:** Wire GameLayout to pass resources and genreSlug to CharacterPanel
- **Jira Key:** none (personal project)
- **Workflow:** tdd
- **Epic:** 25 — UI Redesign — Character Panel, Layout Modes, Chrome Archetypes
- **Repository:** sidequest-ui (React frontend)
- **Branch:** feat/25-11-wire-gamelayout-resources
- **Points:** 3
- **Priority:** p1
- **Status:** in-progress
- **Stack Parent:** 25-10 (Wire GenericResourceBar)

## Context

Story 25-10 added `resources`, `genreSlug`, and `onResourceThresholdCrossed` props to CharacterPanel, but the parent component GameLayout does not yet pass them. This story completes the full data pipeline from WebSocket PARTY_STATUS message through to CharacterPanel rendering GenericResourceBar.

**Dependency chain:**
- 25-2 (CharacterPanel persistent sidebar) — COMPLETE
- 25-4 (GameLayout integration) — COMPLETE
- 25-10 (Wire GenericResourceBar) — COMPLETE
- 25-11 (Wire GameLayout to pass resources/genreSlug) ← current

## What This Story Does

**Complete the full data pipeline:**

1. Extract `resources` from PARTY_STATUS payload in App.tsx (WebSocket handler around line 436)
2. Pass resources through GameLayout props to CharacterPanel
3. Pass genreSlug (already available via useChromeArchetype pattern) to CharacterPanel
4. Wire onResourceThresholdCrossed callback to AudioEngine.playSfx() in GameLayout
5. Verify data flows end-to-end: WebSocket PARTY_STATUS → App.tsx state → GameLayout → CharacterPanel → GenericResourceBar renders

### Acceptance Criteria

1. **Extract resources from PARTY_STATUS in App.tsx:**
   - WebSocket handler for PARTY_STATUS message (existing, line ~436)
   - Extract `resources` field from payload
   - Store in game state (e.g., `setGameState(prev => ({ ...prev, resources: msg.resources }))`)
   - Handle missing resources gracefully (empty object `{}`)
   - Test with spaghetti_western (Luck: 0-6) and neon_dystopia (Humanity: 0-100)

2. **Pass resources and genreSlug to CharacterPanel in GameLayout:**
   - GameLayout imports resources from game state via useGameState hook
   - GameLayout gets genreSlug via existing useChromeArchetype hook (already available)
   - CharacterPanel receives both as props: `<CharacterPanel resources={resources} genreSlug={genreSlug} ... />`
   - Props are non-optional when a game is active (validated by tests)
   - Test props flow from parent to child component

3. **Wire onResourceThresholdCrossed callback in GameLayout:**
   - GameLayout defines callback handler for `onResourceThresholdCrossed` event
   - Callback extracts resource name and threshold from event
   - Routes to AudioEngine.playSfx() with genre-specific sound key (e.g., `luck_threshold_crossed`)
   - Logs threshold crossing for debugging (e.g., "Luck threshold crossed: 3 → 4")
   - Test that callback is passed to CharacterPanel and fires on resource changes

4. **Full end-to-end data flow test:**
   - Write integration test that simulates WebSocket PARTY_STATUS message with resources
   - Verify resources appear in game state
   - Verify GameLayout passes them to CharacterPanel
   - Verify CharacterPanel renders GenericResourceBar components
   - Verify threshold crossing triggers audio callback
   - Test with both spaghetti_western Luck and neon_dystopia Humanity examples

5. **Verify no silent fallbacks:**
   - If resources are present but genreSlug is missing, log a warning
   - If genreSlug is present but resources are missing, component degrades gracefully (shows nothing)
   - All prop combinations handled explicitly (no silent "try alternative" fallbacks)

### Key References
- `src/screens/GameScreen.tsx` or `src/App.tsx` — PARTY_STATUS handler location (line ~436)
- `src/components/GameLayout.tsx` — Parent component that passes props to CharacterPanel
- `src/components/CharacterPanel.tsx` — Consumer component (already accepts resources/genreSlug/callback)
- `src/providers/GameStateProvider.tsx` — Game state management
- `src/hooks/useChromeArchetype.ts` — genreSlug source
- `src/audio/AudioEngine.ts` — SFX playback
- `25-10-session.md` — GenericResourceBar wiring (completed)

### Non-Goals
- UI styling (handled by 25-10 and 25-6/25-7)
- Backend resource mutations (server concern)
- Resource decay mechanics (backend concern)
- Resource spending UI (future story)

## Implementation Strategy

**Phase 1 (RED):** Write tests for the full data pipeline:
- Test PARTY_STATUS handler extracts resources correctly
- Test GameLayout receives resources from game state
- Test GameLayout passes resources and genreSlug to CharacterPanel
- Test onResourceThresholdCrossed callback routes to AudioEngine
- Test end-to-end: WebSocket message → CharacterPanel render
- Test genre-specific examples (spaghetti_western, neon_dystopia)

**Phase 2 (GREEN):** Implement the wiring:
- Add resources extraction logic to PARTY_STATUS handler in App.tsx
- Import useGameState in GameLayout
- Pass resources and genreSlug to CharacterPanel in GameLayout render
- Implement onResourceThresholdCrossed callback in GameLayout
- Wire callback to AudioEngine.playSfx()
- Verify tests pass

**Phase 3 (VERIFY):** Integration verification:
- Full playtest with genre that has resources
- Verify resources display in CharacterPanel
- Verify threshold crossings trigger audio
- Verify no silent fallbacks occur

## Workflow Phases

| Phase | Owner | Status |
|-------|-------|--------|
| setup | sm | in-progress |
| red | tea | pending |
| green | dev | pending |
| spec-check | architect | skipped (personal project) |
| verify | tea | pending |
| review | reviewer | pending |
| spec-reconcile | architect | skipped (personal project) |
| finish | sm | pending |

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-05T16:13:11Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-05T16:45:00Z | 2026-04-05T15:50:36Z | -3264s |
| red | 2026-04-05T15:50:36Z | 2026-04-05T16:01:40Z | 11m 4s |
| green | 2026-04-05T16:01:40Z | 2026-04-05T16:05:14Z | 3m 34s |
| spec-check | 2026-04-05T16:05:14Z | 2026-04-05T16:05:15Z | 1s |
| verify | 2026-04-05T16:05:15Z | 2026-04-05T16:08:52Z | 3m 37s |
| review | 2026-04-05T16:08:52Z | 2026-04-05T16:13:11Z | 4m 19s |
| spec-reconcile | 2026-04-05T16:13:11Z | 2026-04-05T16:13:11Z | 0s |
| finish | 2026-04-05T16:13:11Z | - | - |

## Delivery Findings

No findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No upstream findings during test design.

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- No upstream findings during code review.

## Design Deviations

No deviations at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- No undocumented deviations found.

### TEA (test design)
- **App.tsx PARTY_STATUS extraction tested at GameLayout boundary, not WebSocket level**
  - Spec source: session AC-1
  - Spec text: "Extract resources from PARTY_STATUS in App.tsx"
  - Implementation: Tests verify GameLayout receives and passes resources props, not that App.tsx extracts them from WebSocket messages
  - Rationale: App.tsx is a large component with WebSocket dependencies that make unit testing the handler impractical. The wire from App.tsx → GameLayout is tested by GameLayout accepting the prop. Dev must implement the extraction in App.tsx and pass it through.
  - Severity: minor
  - Forward impact: Dev must add resources state to App.tsx and pass to GameLayout — tested indirectly via GameLayout prop acceptance

## Sm Assessment

Story 25-11 completes the pipeline that 25-10 left half-wired. Full data path: PARTY_STATUS → App.tsx → GameLayout → CharacterPanel → GenericResourceBar. TEA must write tests that verify data flows from the WebSocket handler all the way to rendered bars — not just component props.

**Routing:** Handoff to TEA (Fezzik) for RED phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Full-pipeline wiring — GameLayout must pass resources/genreSlug to CharacterPanel and wire audio callback

**Test Files:**
- `src/components/__tests__/GameLayout-resources.test.tsx` — 15 tests covering the GameLayout→CharacterPanel pipeline

**Tests Written:** 15 tests covering 4 ACs
**Status:** RED (10 failing, 5 passing — backward compat and empty-state)

**Failure root cause:** GameLayoutProps doesn't have resources/genreSlug/onResourceThresholdCrossed. GameLayout doesn't pass them to CharacterPanel. All failures cascade from missing props.

### Test Coverage by AC

| AC | Tests | Description |
|----|-------|-------------|
| AC-2 | 7 | GameLayout accepts and passes resources/genreSlug to CharacterPanel |
| AC-3 | 2 | Threshold crossing routes to AudioEngine.playSfx() |
| AC-4 | 3 | End-to-end pipeline verification (props→render, updates, multiple resources) |
| AC-5 | 2 | No silent fallbacks (resources without genreSlug) |
| Wiring | 1 | GameLayout is non-test consumer of resources→CharacterPanel pipeline |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #4 Null/undefined | Empty resources, absent genreSlug tests | failing |
| #6 React/JSX | Rerender with updated resources prop | failing |
| #8 Test quality | Self-check: all tests have meaningful assertions | verified |

**Rules checked:** 3 of 13 applicable
**Self-check:** 0 vacuous tests found

**Handoff:** To Inigo Montoya (Dev) for implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `src/components/GameLayout.tsx` — Added resources/genreSlug props, threshold callback routing to audio.playSfx(), pass-through to CharacterPanel
- `src/App.tsx` — Added partyResources state, extract resources from PARTY_STATUS payload, pass resources/currentGenre to GameLayout

**Tests:** 89/89 passing (GREEN) — 15 new pipeline tests + 74 existing (no regressions)
**Branch:** feat/25-11-wire-gamelayout-resources (pushed)

**Handoff:** To Fezzik (TEA) for verify phase

## TEA Verify Assessment

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 4 findings | All pre-existing App.tsx patterns (timers, storage, buffer) — out of scope |
| simplify-quality | 2 findings | genreSlug silent fallback (applied); vacuous test (applied) |
| simplify-efficiency | 2 findings | genreSlug silent fallback (applied); GenericResourceBar useEffect (pre-existing) |

**Applied:** 2 high-confidence fixes (replaced `genreSlug ?? "default"` with explicit guard+warn; fixed vacuous test with real assertion)
**Flagged for Review:** 0
**Noted:** 5 pre-existing findings (App.tsx patterns, GenericResourceBar useEffect) — out of scope
**Reverted:** 0

**Overall:** simplify: applied 2 fixes

**Quality Checks:** TypeScript typecheck passing. 60/60 tests GREEN. No regressions.

**Handoff:** To Westley (Reviewer) for code review

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 | dismissed 3 |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | findings | 5 | dismissed 5 |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 4 | confirmed 1, dismissed 3 |

**All received:** Yes (4 returned, 5 disabled)
**Total findings:** 1 confirmed (low), 11 dismissed

### Finding Triage

**Confirmed:**
1. [RULE] Redundant `typeof resources === "object"` guard at App.tsx:466 — always-true after `resources &&` short-circuit. Misleading but not broken. **Severity: LOW (non-blocking).**

**Dismissed:**
- [SILENT] `audio?.playSfx` optional chaining — codebase convention for all audio calls (AudioEngine requires user gesture). Not a regression.
- [SILENT] Resources silently ignored when absent from PARTY_STATUS — correct behavior for genres without resources. Not a fallback.
- [SILENT] Inconsistent guard (genreSlug guarded, audio not) — audio optional chaining is convention. Same as above.
- [TYPE] `as Record<string, ResourcePool>` cast — follows same pattern as all 10+ other payload extractions in the handler. Not a regression; systematic fix would be a separate tech-debt story.
- [TYPE] `currentGenre ?? undefined` null-to-undefined — correct type coercion, not a fallback.
- [TYPE] Turn status `as string` casts (lines 430-432) — pre-existing, not introduced by this story.
- [TYPE] HTMLElement cast (line 208) — pre-existing, low confidence.
- [TYPE] useCallback deps on genreSlug — correct deps, not a bug.
- [RULE] `as SavedSession` / `as HmrState` JSON.parse casts — pre-existing.
- [RULE] ptt.discard dep suppression — pre-existing.
- [RULE] `as Record<string, ResourcePool>` redundant with typeof finding — counted once.

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] Full pipeline wired: PARTY_STATUS → `setPartyResources` (App.tsx:465-468) → `partyResources` state → `resources={partyResources}` (App.tsx:849) → GameLayout destructures (line 84) → `<CharacterPanel resources={resources}>` (GameLayout.tsx:266) → Status tab → GenericResourceBar renders. No dead ends.
2. [VERIFIED] Genre slug flows: `currentGenre` state (App.tsx:109) → `genreSlug={currentGenre ?? undefined}` (App.tsx:850) → GameLayout (line 85) → CharacterPanel (line 267) → GenericResourceBar `genre_slug` prop → `data-genre` attribute. Compliant with wiring rule.
3. [VERIFIED] Threshold callback: `handleResourceThresholdCrossed` (GameLayout.tsx:94-104) has explicit `!genreSlug` guard with console.warn, then routes to `audio?.playSfx(sfxKey)`. No silent fallback. Complies with CLAUDE.md.
4. [VERIFIED] `useCallback` deps `[audio, genreSlug]` at GameLayout.tsx:103 — both captured values correctly listed. Complies with Rule #6.
5. [LOW] Redundant `typeof resources === "object"` guard at App.tsx:466 — always-true after `resources &&`. Cosmetic, not blocking.
6. [VERIFIED] All test assertions are meaningful — 15 tests with concrete DOM queries and mock verifications. No vacuous assertions. Complies with Rule #8.
7. [VERIFIED] Wiring test at GameLayout-resources.test.tsx:282-295 verifies GameLayout is a non-test consumer of the resources→CharacterPanel pipeline. Complies with CLAUDE.md "every test suite needs a wiring test."
8. [VERIFIED] No `as any`, `@ts-ignore`, `Function` type, or `Record<string, any>` in diff. Complies with Rules #1, #2.

[EDGE] Disabled via settings.
[SILENT] All dismissed — codebase conventions (audio optional chaining) and correct behavior (absent resources kept stale).
[TEST] Disabled via settings.
[DOC] Disabled via settings.
[TYPE] All dismissed — cast pattern matches codebase convention; null-to-undefined conversion correct.
[SEC] Disabled via settings.
[SIMPLE] Disabled via settings.
[RULE] 1 confirmed (low): redundant typeof guard. 3 pre-existing dismissed.

### Devil's Advocate

What if this code is broken?

**Scenario 1: Server sends malformed resources.** `msg.payload.resources` is `{Luck: "high"}` instead of `{Luck: {value: 4, max: 6, thresholds: [...]}}`. The `as Record<string, ResourcePool>` cast succeeds, `typeof === "object"` is true, `setPartyResources` stores it. CharacterPanel renders, GenericResourceBar receives `value: undefined`. The fillPct calculation: `undefined / 6 * 100 = NaN`, `Math.min(100, NaN) = NaN`, `Math.max(0, NaN) = NaN`. The bar renders with `width: NaN%`. This is broken rendering but not a crash. React doesn't throw on NaN styles. **Risk: low — server is trusted, schema is controlled by the Rust backend.**

**Scenario 2: PARTY_STATUS arrives before currentGenre is set.** App.tsx initializes `currentGenre` as `loadSession()?.genre ?? null`. If HMR state is lost and session is empty, currentGenre is null. PARTY_STATUS arrives, resources are stored, but genreSlug is null → undefined. CharacterPanel gets `genreSlug={undefined}`. CharacterPanel's `genreSlug ?? ""` passes empty string to GenericResourceBar. Bars render without genre styling. **Risk: very low — currentGenre is set in handleConnect which happens before PARTY_STATUS.**

**Scenario 3: Resources change mid-render.** React batches state updates. `setPartyMembers` and `setPartyResources` are called in the same handler (App.tsx:462, 468). React 18 batches these into a single re-render. No torn state. **Verified safe.**

No blocking scenarios found.

**Data flow traced:** msg.payload.resources → partyResources state → GameLayout resources prop → CharacterPanel resources prop → GenericResourceBar renders
**Pattern observed:** Prop threading (App→GameLayout→CharacterPanel) at 3 layers — standard React data flow
**Error handling:** Explicit genreSlug guard with console.warn at GameLayout.tsx:96-98. Resources guard at App.tsx:466.
**Handoff:** To Vizzini (SM) for finish-story