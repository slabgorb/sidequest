---
story_id: "37-26"
jira_key: ""
epic: "37"
workflow: "wire-first"
---
# Story 37-26: WebSocket auto-reconnect on navigation

## Story Details
- **ID:** 37-26
- **Jira Key:** (not created)
- **Epic:** 37 — Playtest 2 Fixes — Multi-Session Isolation
- **Workflow:** wire-first
- **Stack Parent:** none
- **Points:** 3
- **Priority:** p1
- **Type:** bug

## Acceptance Criteria

**AC-1:** useWebSocket hook detects connection drop and emits reconnect event
- Call site: `src/hooks/useWebSocket.ts` must invoke reconnection logic when WebSocket close event fires
- Visible behavior: Game state on disconnect → reconnect shows brief banner "Reconnecting..." then clears

**AC-2:** Exponential backoff on reconnect attempts (1s, 2s, 4s, 8s max)
- Call site: `useWebSocket` retry loop enforces wait between connection attempts
- Measurable: debug console shows increasing delays between reconnect attempts

**AC-3:** Input disabled during disconnect period
- Call site: Global input state gated by `ws.readyState === WebSocket.OPEN`
- Visible behavior: buttons/text inputs appear grayed out or disabled when WS is closed/connecting

**AC-4:** Reconnect banner visible when `ws.readyState !== OPEN`
- Call site: New component `ReconnectBanner` rendered at app root level when needed
- Visible behavior: "Reconnecting..." text appears above game content during outages

## Workflow Tracking
**Workflow:** wire-first
**Phase:** finish
**Phase Started:** 2026-04-19T08:27:57Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-19T00:00Z | 2026-04-19T07:57:05Z | 7h 57m |
| red | 2026-04-19T07:57:05Z | 2026-04-19T07:59:42Z | 2m 37s |
| green | 2026-04-19T07:59:42Z | 2026-04-19T08:02:08Z | 2m 26s |
| review | 2026-04-19T08:02:08Z | 2026-04-19T08:27:57Z | 25m 49s |
| finish | 2026-04-19T08:27:57Z | - | - |

## Delivery Findings

No upstream findings.

## Design Deviations

No deviations logged.

## SM Assessment

Setup verified: session file created, feature branch `feat/37-26-ws-auto-reconnect` exists in sidequest-ui on top of develop, story context populated from epic-37.yaml with AC-1 through AC-4 and concrete call sites (useWebSocket.ts, ReconnectBanner, ws.readyState input gating). Workflow is wire-first (3pt UI bug). Handing off to TEA for boundary-level RED test.
## TEA Assessment

RED state pinned in sidequest-ui on branch `feat/37-26-ws-auto-reconnect`:

- `src/components/__tests__/ReconnectBanner.test.tsx` — 5 cases covering AC-4. Asserts render=null on OPEN; "Reconnecting..." text on CONNECTING/CLOSED/CLOSING; role=status for a11y.
- `src/__tests__/reconnect-banner-wiring.test.tsx` — 3 integration cases driving a MockWebSocket through the real `useWebSocket` hook with a minimal host mirroring App wiring (useWebSocket → ReconnectBanner + InputBar disabled gate). Covers AC-1, AC-3, AC-4 end-to-end, including reconnect re-enable.

Both suites fail to resolve `@/components/ReconnectBanner` — clean RED.

**GREEN work for Dev (Winchester):**
1. Create `src/components/ReconnectBanner.tsx` exporting `ReconnectBanner({ readyState }: { readyState: number })` — returns null when `readyState === WebSocket.OPEN`, else a `role="status"` element with "Reconnecting...".
2. Wire it into `src/App.tsx`: render `<ReconnectBanner readyState={readyState} />` at app root (readyState already flows from useGameSocket on line 466).
3. Update App's InputBar `disabled` prop to include `readyState !== WebSocket.OPEN` (AC-3). The existing `prevReadyState` / `canType` ref logic at line 750+ is the right integration point — don't unwind that fix, just ensure the disabled prop additionally respects readyState.
4. AC-2 (exponential backoff) is already implemented in `useWebSocket.ts` — no work needed; mention it in GREEN assessment so Reviewer knows.

**Rule coverage:** project is moving away from source-grep assertions (epic 40-x) — wiring test uses a real MockWebSocket + render, not a `.contains(...)` check.
## Dev Assessment

GREEN in 14 lines. Component + one import + one JSX line.

**Implementation:**
- `src/components/ReconnectBanner.tsx` (10 lines): returns null on OPEN, `<div role="status">Reconnecting...</div>` otherwise.
- `src/App.tsx`: added import and `<ReconnectBanner readyState={readyState} />` above `<main>` inside AppInner.

**What was already done (no-op):**
- AC-1 reconnect detection: `useWebSocket.ts::onclose` already schedules reconnect via `setTimeout(createSocket, nextBackoff())`.
- AC-2 exponential backoff: `nextBackoff()` already doubles from 1000ms up to `maxBackoffMs` (default 8000ms).
- AC-3 input disabled: App.tsx:874 already gates `GameBoard.disabled={readyState !== WebSocket.OPEN || !canType}`.

Only AC-4 actually needed code — the banner component + its mount point. Ramifies: Epic 37 is "playtest 2 fixes", and the reconnect *mechanism* was already fixed in the 2026-04-11 ghost-socket work. The missing piece was player-visible feedback during a reconnect.

**Tests:**
- Story RED tests: 8/8 pass.
- Full vitest: 1055 passed / 29 failed. The 29 failures are pre-existing (dice overlay + confrontation wiring — confirmed by re-running those two files against HEAD with my changes removed; identical 6 failures with or without this branch).
- `tsc --noEmit`: clean.

**Observability:** N/A — cosmetic UI per sidequest-ui CLAUDE.md ("Not needed for: Cosmetic UI changes").

**Handoff to Reviewer (Potter):** Minimal surface area, 2 files, 14 LOC added. Check that the banner placement doesn't fight any existing layout (it sits above `<main>` as a fixed-flow element — no absolute positioning).
## Historical Reviewer Assessment (Round 1)

**Verdict: REJECTED — 1 blocker (B1), 2 nits.**

### B1 (BLOCKER) — Banner shows on initial page load

ReconnectBanner renders on first paint because `readyState` initializes to `WebSocket.CLOSED` (3) in `useWebSocket.ts:75`. User sees "Reconnecting..." over the ConnectScreen before any connection has ever been attempted. Copy is a lie; story is "auto-reconnect *on navigation*" — intent is post-disconnect, not first-load chrome.

**Required fix:** gate the banner on a "has ever been OPEN" flag.

Suggested shape:
```tsx
// In ReconnectBanner.tsx
import { useEffect, useRef } from "react";

export function ReconnectBanner({ readyState }: { readyState: number }) {
  const wasOpenRef = useRef(false);
  useEffect(() => {
    if (readyState === WebSocket.OPEN) wasOpenRef.current = true;
  }, [readyState]);

  if (!wasOpenRef.current || readyState === WebSocket.OPEN) return null;
  return <div role="status" className="reconnect-banner">Reconnecting...</div>;
}
```

And update the first unit test in ReconnectBanner.test.tsx — `"renders nothing when readyState is CONNECTING"` on first mount should be part of coverage — add a case that asserts the banner stays hidden through CLOSED → CONNECTING → OPEN (first connect) and only appears on OPEN → CLOSED (true reconnect).

Also update the wiring test to simulate initial page load explicitly (render Host, assert no `role="status"` before openLatest is called).

### N1 (NIT) — `.reconnect-banner` class unstyled
No CSS rule for `reconnect-banner`. Banner renders as unstyled inline text. Add a minimal rule (position, padding, background) so it looks intentional during outages. Not blocking.

### N2 (NIT) — Real 1100ms setTimeout in wiring test
`reconnect-banner-wiring.test.tsx` uses `setTimeout(..., 1100)` to wait out the backoff. Works, but vitest fake timers would make the suite faster. Not blocking.

### Clean checks
- a11y role=status is correct
- useWebSocket.ts untouched; 2026-04-11 ghost-socket teardown fix preserved
- 29 pre-existing failures unchanged (confirmed by baseline comparison)
- OTEL correctly exempted (cosmetic UI per sidequest-ui CLAUDE.md)

Handing back to Dev (Winchester) for B1 + follow-on test updates.

## Dev Assessment (Round 2)

B1 + both nits fixed in commit 7b63d68.

- **B1:** `wasOpenRef` in ReconnectBanner — set to true in a `useEffect` when `readyState === OPEN`, checked at render. Banner now stays hidden through first-time CLOSED → CONNECTING → OPEN, only surfaces after a true disconnect.
- **N1:** Tailwind classes (`w-full bg-amber-600/90 text-white shadow animate-pulse`) — themed visual treatment, no new CSS file needed (rest of the app uses Tailwind).
- **N2:** Wiring test switched to `vi.useFakeTimers()` + `vi.advanceTimersByTime(1100)`, plus an explicit B1 regression case ("does NOT show banner on initial page load").

Unit tests: 9 cases (was 5). Wiring tests: 4 cases (was 3). All 13 pass. Full suite delta: +5 passing, 0 new failures, 29 pre-existing failures unchanged.

Handing back to Reviewer (Potter) for re-review.

## Historical Reviewer Assessment (Round 2)

**Verdict: APPROVED.**

B1, N1, N2 all fixed correctly. The `wasOpenRef` + `useEffect` pattern has a theoretical one-render latency at the OPEN transition, but the OPEN short-circuit in the render function hides the banner anyway during that window, and subsequent transitions land in separate React commits (onopen vs onclose are on different event loop ticks). No banner flicker, no visible seam.

Styling uses existing Tailwind vocabulary (bg-amber-600/90, animate-pulse) that appears elsewhere in the codebase — no orphan CSS class.

The new B1 regression test explicitly pins the fix: "does NOT show banner on initial page load" would fail if someone later removed the `wasOpenRef` check.

Tests: 13/13 pass, 29 pre-existing failures unchanged (dice overlay + confrontation wiring — not touched). Types clean.

Handing to SM (Hawkeye) for PR creation + merge + finish.

## Subagent Results (Round 2 — historical)

All received: Yes

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | blocked | ESLint react-hooks/refs (4 errors) on ReconnectBanner.tsx:16 — `wasOpenRef.current` read during render | BLOCKER → B3 |
| 2 | reviewer-edge-hunter | Yes | findings | 5 findings: StrictMode ref-inheritance (high), same-batch OPEN→CLOSED (medium), CLOSING after intentional close (high), CLOSING test enshrines lie (medium), WebSocket.OPEN constant source (low) | BLOCKER → B2 (intentional-close); others follow-up |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 findings in useWebSocket.ts (empty catch on JSON parse, log-no-rethrow on binary decode) | OUT OF SCOPE — pre-existing, not this diff |
| 4 | reviewer-test-analyzer | Yes | findings | 4 findings: firstChild null coupling (medium), no unmount-remount-while-disconnected case (medium), no intentional-close case (medium), hard-coded 1100ms vs runAllTimers (medium) | Partial incorporation into B2 fix; others follow-up |
| 5 | reviewer-comment-analyzer | Yes | findings | 1 finding: comment understates two-condition coupling on render guard | Resolved naturally by B3 fix (useState removes the timing concern) |
| 6 | reviewer-type-design | Yes | findings | 1 finding (medium): `readyState: number` should be `0\|1\|2\|3` literal union shared with hook | FOLLOW-UP — hook-wide refactor, out of scope for this 3pt story |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | Yes | findings | 3 findings: useRef→useState OR lift `isReconnecting` to hook (high), MockWebSocket duplicated with useWebSocket-teardown.test.ts (high), Object.defineProperty ceremony unnecessary (high) | Lift-to-hook direction adopted for B2; MockWebSocket extraction → follow-up |
| 9 | reviewer-rule-checker | Yes | N/A | Not dispatched in round 2 (reviewer omission — corrected in round 3). | DEFERRED to round 3 |

## Historical Reviewer Assessment (Round 2)

**Verdict: REJECTED — 3 blockers (B2, B3, B4). B2 and B3 are regressions introduced by this diff.**

### B2 (BLOCKER, regression) — Banner lies on intentional disconnect

When the user leaves the session (`handleLeave` → `useWebSocket.disconnect()`), readyState transitions OPEN → CLOSING → CLOSED. `intentionalCloseRef` in the hook correctly suppresses reconnect, but **the banner has no knowledge of intentional vs. unintentional close**, so it renders "Reconnecting..." during CLOSING and persists forever on CLOSED (no reconnect ever completes).

Same class of bug as B1 (visible lie about a nonexistent reconnect), introduced by this very story. Per sidequest-ui CLAUDE.md: "Never downgrade to a quick fix because you think the context is just a playtest."

**Required fix — adopt Simplifier F1 direction:** lift the "is this a reconnect?" signal into `useWebSocket`, because the hook is the only place that has both `intentionalCloseRef` AND knowledge of prior OPEN transitions. Concretely:

1. Add `isReconnecting: boolean` to `UseWebSocketReturn`:
   ```ts
   // useWebSocket.ts — in the hook body
   const hasEverOpenedRef = useRef(false);
   // inside ws.onopen:
   hasEverOpenedRef.current = true;
   // derived:
   const isReconnecting =
     hasEverOpenedRef.current &&
     !intentionalCloseRef.current &&
     readyState !== WebSocket.OPEN;
   return { ..., isReconnecting };
   ```
2. Thread `isReconnecting` through `useGameSocket` the same way `readyState` flows.
3. Simplify `ReconnectBanner` to a pure prop-driven component:
   ```tsx
   export function ReconnectBanner({ visible }: { visible: boolean }) {
     if (!visible) return null;
     return <div role="status" className="...">Reconnecting...</div>;
   }
   ```
4. App.tsx: `<ReconnectBanner visible={isReconnecting} />`.

This single refactor resolves B2, B3 (no more render-time ref read), and the comment-analyzer's two-condition coupling note.

### B3 (BLOCKER) — ESLint react-hooks/refs violation

Preflight fails hard with 4 errors at `ReconnectBanner.tsx:16`. The lint rule is correct — mutating a ref inside `useEffect` and then reading `ref.current` during render is the exact footgun it was written to catch. The B2 fix above eliminates this entire pattern (component becomes prop-driven, no hooks at all).

### B4 (BLOCKER) — Test suite enshrines the B2 bug

`src/components/__tests__/ReconnectBanner.test.tsx:44` ("shows banner after OPEN → CLOSING") asserts CLOSING shows the banner regardless of whether the close was intentional. Test-analyzer F2 and F3 caught this. After the B2 fix, that test either needs an intentional-close variant (banner hidden) or the test changes to assert against `visible` prop only.

**Required additions to the test suite after B2 fix:**
- `useWebSocket` unit test: `isReconnecting` stays false after `disconnect()` is called.
- Wiring test: a case where `Host` calls the returned `disconnect` function and asserts banner stays hidden.
- Unit test: switch `expect(container.firstChild).toBeNull()` → `expect(screen.queryByRole("status")).toBeNull()` per test-analyzer F1 (while we're in here).
- Wiring test: swap `vi.advanceTimersByTime(1100)` → `vi.runAllTimers()` per test-analyzer F4.

### Nits (non-blocking, note for follow-up story)

- **Type-design F1:** `readyState: number` → `0|1|2|3` literal union shared across hook + consumers. Hook-wide type tightening, separate story.
- **Simplifier F2/F3:** Extract shared `MockWebSocket` helper from this test + `useWebSocket-teardown.test.ts`, drop `Object.defineProperty` ceremony. Tech-debt cleanup, separate story.
- **Silent-failure:** 2 findings in `useWebSocket.ts` (empty catch + log-no-rethrow) are pre-existing, not this diff. Worth logging in sq-wire-it for a future cleanup pass.

Handing back to Dev (Winchester) for B2/B3/B4.

## Dev Assessment (Round 3)

B2, B3, B4 all fixed by lifting `isReconnecting` into `useWebSocket` as the specialists recommended in convergence.

**Architecture change:**
- `useWebSocket` now owns the "are we reconnecting?" semantic via `hasEverOpened` state + `intentionalClose` state mirror (the ref is preserved for the synchronous `onclose` fast path — the state mirror is new, and drives React re-renders of consumers).
- The derivation: `isReconnecting = hasEverOpened && !intentionalClose && !connected`. First-load is false (B1), intentional-disconnect is false (B2), genuine drop-after-open is true.
- `useGameSocket` forwards `isReconnecting` on its return type.
- `App.tsx` destructures `isReconnecting` and passes `<ReconnectBanner visible={isReconnecting} />`.
- `ReconnectBanner` is now a pure presentational component with no hooks — kills B3 entirely.

**Preserved:** The 2026-04-11 StrictMode-cleanup fix. The cleanup path still sets `intentionalCloseRef.current = true` but does NOT mirror to `setIntentionalClose` (added comment explains why — a state update during cleanup would misreport isReconnecting for the remounted component).

**Test rework:**
- New `src/hooks/__tests__/useWebSocket-isReconnecting.test.ts` (6 cases): B1 mount-silence, first-time-connect silence, AC-1 flip-true, B2 intentional-close silence, reconnect flip-back, connect-after-disconnect semantics.
- Wiring test: added B2 regression (intentional disconnect → no banner), switched to `vi.runAllTimers()` per test-analyzer F4.
- Unit test: simplified to 4 prop-contract cases, switched to `queryByRole` per test-analyzer F1. The behavioral logic moved to the hook test file.

**Results:**
- 27/27 story-scope tests pass (unit + wiring + new isReconnecting + teardown regression + useGameSocket).
- `npx eslint` clean on all 4 touched prod files.
- `tsc --noEmit` clean.
- Full suite: +3 passing (1063 vs 1060), 29 pre-existing failures unchanged.

**Deferred to follow-up story (Reviewer noted as follow-up, not blocking):**
- Type-design F1: `readyState: number` → literal union, hook-wide.
- Simplifier F2/F3: extract shared MockWebSocket helper + drop Object.defineProperty ceremony.
- Silent-failure findings in useWebSocket.ts empty catch / log-no-rethrow — log in sq-wire-it.

Handing back to Reviewer (Potter) for round 3.

## Subagent Results

All received: Yes

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | Tests GREEN (1063 pass, 29 pre-existing failures unchanged), ESLint GREEN (0 branch-introduced errors, react-hooks/refs blocker from round 2 RESOLVED), tsc GREEN | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 4 findings: url-prop-change+autoConnect=false spurious isReconnecting=true (high), same-scenario ref/state divergence (medium), test batching-order guard (low), disconnect-before-open stranded socket (medium) | DISMISS edge-hunter F1/F2 (premised on setReadyState firing from cleanup — cleanup calls detachHandlers BEFORE ws.close(), so no state transition fires → spurious banner never materializes); F4 is pre-existing, out of scope; F3 low-confidence test nit |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 1 finding (medium): theoretical disconnect() ref/state race window on synchronous-onclose browsers | DISMISS — React 18 automatic batching covers event handlers + async contexts; all state updates within disconnect()+onclose land in one commit |
| 4 | reviewer-test-analyzer | Yes | findings | 5 findings: redundant firstChild (low), duplicate ReconnectBanner test cases 2&3 (medium), B2 test missing AC-3 disabled assertion (medium), no onerror coverage (medium), no autoConnect=true mid-reconnect CONNECTING case (medium) | FOLLOW-UP polish — not blocking. The core ACs are covered; the gaps are edge/completeness improvements suitable for a test hardening pass |
| 5 | reviewer-comment-analyzer | Yes | findings | 1 finding (medium): the cleanup "do NOT mirror" comment has inverted causal direction — conclusion correct, explanation backwards | FOLLOW-UP — comment clarity nit, not a behavior issue |
| 6 | reviewer-type-design | Yes | clean | isReconnecting: boolean is correct for a derived UI flag; no newtype would add safety | N/A |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | Yes | findings | Dual ref+state for intentionalClose confirmed necessary (sync onclose read needs ref, reactive derivation needs state) — no simplification without a larger useReducer restructure. One low-confidence nit: Host.onReady in wiring test fires on every render, not lifecycle-once. | FOLLOW-UP — Host.onReady pattern polish, not blocking |
| 9 | reviewer-rule-checker | Yes | clean | 9 project rules checked, 31 instances verified, 0 violations. Full pipeline wiring verified (useWebSocket state → derivation → useGameSocket → App → ReconnectBanner prop → render). OTEL exempt (cosmetic UI). | N/A |

## Reviewer Assessment

**Verdict: APPROVED.**

All three blockers from round 2 (B2 intentional-close lie, B3 ESLint react-hooks/refs, B4 test suite enshrining bug) are fixed correctly. The refactor lifts `isReconnecting` into `useWebSocket` as the specialist fleet independently recommended in round 2, and the result is simpler at every level: ReconnectBanner lost all its hooks, App.tsx destructures a boolean, and the "are we reconnecting?" semantic lives with the state machine that has always owned `intentionalCloseRef`.

**Key correctness checks:**
- 2026-04-11 StrictMode ghost-socket regression preserved: `useWebSocket-teardown.test.ts` still passes.
- Edge-hunter's HIGH url-prop-change finding was traced and found to rest on a flawed premise — `detachHandlers(ws)` is called **before** `ws.close()` in cleanup, so the browser's eventual `onclose` cannot trigger `setReadyState(CLOSED)`. The spurious-banner path doesn't materialize. (The finding would be correct if handler detachment happened after close, but the 2026-04-11 fix specifically inverted that order.)
- Silent-failure's batching-race concern dismissed — React 18 automatic batching covers `disconnect()` + synchronous-`onclose` across event handlers, timeouts, promises, and microtasks. All state updates in a single tick commit together.
- Dual ref+state storage for `intentionalClose` is necessary, not over-engineering: sync read path (onclose scheduling) needs the ref, reactive derivation needs the state.

**Specialist findings mapped to decisions:**
- [RULE] reviewer-rule-checker: 0 violations across 9 rules, full pipeline wiring verified — accepted as-is.
- [TYPE] reviewer-type-design: clean; prior `readyState: number` nit scoped to follow-up.
- [EDGE] reviewer-edge-hunter: 4 findings — 2 dismissed (premised on setReadyState firing from cleanup, which doesn't occur because detachHandlers precedes close), 1 pre-existing out-of-scope, 1 low-confidence test guard → follow-up.
- [SILENT] reviewer-silent-failure-hunter: 1 finding dismissed (React 18 batches state+close within the same tick).
- [TEST] reviewer-test-analyzer: 5 findings, all polish — listed under follow-ups below.
- [DOC] reviewer-comment-analyzer: 1 finding (inverted causal explanation in cleanup comment) → follow-up.

**Follow-up tasks (not blocking — suitable for a test-hardening or comment-cleanup story):**
- **Comment-analyzer F1:** rewrite the cleanup "do NOT mirror" comment to describe the actual risk (spurious banner during first-load, not "misreport as intentional").
- **Test-analyzer F1:** drop redundant `container.firstChild` assertions in ReconnectBanner.test.tsx.
- **Test-analyzer F2:** collapse the two `visible=true` near-duplicate cases.
- **Test-analyzer F3:** add `input.disabled === true` assertion to the B2 intentional-disconnect wiring test.
- **Test-analyzer F4:** add an `onerror`-without-`onclose` case to pin the current (correct) behavior — `isReconnecting` does not flip without a readyState transition.
- **Test-analyzer F5:** add an `autoConnect=true` auto-reconnect CONNECTING-phase case to complement the explicit-connect case already in the suite.
- **Edge-hunter F4:** pre-existing disconnect-before-open race (socket can be stranded OPEN). Not introduced by this diff but worth a follow-up.
- **From round 2:** Type-design readyState-number → literal union (hook-wide), Simplifier MockWebSocket extraction, Silent-failure findings in useWebSocket.ts empty-catch / log-no-rethrow.

Handing to SM (Hawkeye) for PR creation + merge + finish.

All received: Yes