---
story_id: "18-2"
epic: "18"
workflow: "tdd"
---

# Story 18-2: Fix State Tab — Wire GameStateSnapshot to Dashboard Listener

## Story Details
- **ID:** 18-2
- **Epic:** 18 — OTEL Dashboard — Granular Instrumentation & State Tab
- **Type:** Bug
- **Points:** 2
- **Priority:** p1
- **Workflow:** tdd
- **Repos:** api, ui
- **Stack Parent:** none

## Business Context

The OTEL dashboard State tab has never worked. It permanently displays "Waiting for
GameStateSnapshot event..." despite the API correctly emitting snapshot data after
every turn. The GM panel's state explorer is a critical debugging tool — it shows the
full game state tree and turn-over-turn diffs, which is the only way to verify that
subsystems are actually mutating state vs Claude just narrating convincingly.

## Technical Approach

### Root Cause

Event type naming mismatch between emitter and listener:

- **API emits:** `WatcherEventType::GameStateSnapshot` which serializes to `"game_state_snapshot"` via serde snake_case
- **Dashboard expects:** `event.event_type === "state_transition"` (useDashboardSocket.ts:139)

The filter never matches. Snapshots arrive over the WebSocket but are silently discarded
into the raw event stream.

### Fix

Update the dashboard listener to match the actual event type in `useDashboardSocket.ts:139`:

```typescript
// From:
if (event.event_type === "state_transition" && event.fields.snapshot) {
// To:
if (event.event_type === "game_state_snapshot" && event.fields.snapshot) {
```

### Key Files

| File | Change |
|------|--------|
| `sidequest-ui/src/components/Dashboard/hooks/useDashboardSocket.ts` | Fix event type string on line 139 |
| `sidequest-api/crates/sidequest-server/src/lib.rs` | No change — enum is correct |
| `sidequest-api/crates/sidequest-server/src/dispatch/mod.rs` | No change — emit is correct |

## Acceptance Criteria

1. **State tab shows game state** — after completing at least one turn, the State tab
   displays a JSON tree of the full game state (not "Waiting for GameStateSnapshot")
2. **Tree view navigable** — state tree is expandable/collapsible with search filtering
3. **Diff view works** — after two+ turns, Diff view highlights state changes between
   selected turns
4. **Turn selector populated** — dropdown shows all turns with snapshots, labeled by
   turn number and classified intent
5. **Console tab confirms** — raw events in Console tab show `game_state_snapshot` events
   being received and correlated to turns

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-31T22:56:38Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-31T00:00Z | 2026-03-31T22:45:47Z | 22h 45m |
| red | 2026-03-31T22:45:47Z | 2026-03-31T22:47:55Z | 2m 8s |
| green | 2026-03-31T22:47:55Z | 2026-03-31T22:50:04Z | 2m 9s |
| review | 2026-03-31T22:50:04Z | 2026-03-31T22:56:38Z | 6m 34s |
| finish | 2026-03-31T22:56:38Z | - | - |

## Sm Assessment

**Story readiness:** Ready. Root cause identified, fix is a one-line string change in useDashboardSocket.ts:139. Context doc has full technical approach and ACs.

**Jira:** Skipped — personal project, no Jira integration.

**Risks:** None. The fix is surgical — change one string constant. The API emit code and State tab UI are both correct; only the event type filter is wrong.

**Routing:** TDD workflow → TEA for RED phase (write failing tests for the event type match), then Dev for GREEN phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Bug fix — event type mismatch needs regression coverage

**Test Files:**
- `sidequest-ui/src/components/Dashboard/hooks/__tests__/useDashboardSocket.test.ts` — 6 tests covering snapshot wiring through the dashboard reducer

**Tests Written:** 6 tests covering 3 ACs (AC-1, AC-3, AC-4)
**Status:** RED (5 failing, 1 passing — ready for Dev)

| Test | AC | Assertion | Status |
|------|----|-----------|--------|
| populates turn snapshot from game_state_snapshot event | AC-1 | snapshot populated from correct event type | FAILING |
| sets latestSnapshot at dashboard level | AC-1 | latestSnapshot propagates up | FAILING |
| does NOT populate snapshot from state_transition events | AC-1 (negative) | wrong event type must not match | FAILING |
| chains previousSnapshot from prior turn | AC-3 | diff view has both snapshots | FAILING |
| correlates snapshot to existing turn by turn_number | AC-4 | no duplicate turns from snapshot event | FAILING |
| ignores game_state_snapshot without snapshot field | edge | gracefully handles missing field | PASSING |

### Rule Coverage

No lang-review rules applicable — this is a TypeScript event type string fix, not a structural change. Self-check passed: all 6 tests have meaningful assertions (toEqual, toBeNull, toHaveLength, toBe). No vacuous assertions found.

**AC-2 (tree view navigable) and AC-5 (console tab confirms):** Not tested here — AC-2 is a UI rendering concern already handled by StateTab component, AC-5 is a visual verification concern. Both are covered by existing wiring (raw events already appear in Console tab).

**Handoff:** To Yoda (Dev) for implementation — change `"state_transition"` to `"game_state_snapshot"` on line 139.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-ui/src/components/Dashboard/hooks/useDashboardSocket.ts` - Changed event type filter from `"state_transition"` to `"game_state_snapshot"` on line 139

**Tests:** 6/6 passing (GREEN)
**Branch:** feat/18-2-fix-state-tab-wiring (pushed)

**Handoff:** To next phase (review)

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (lint prefer-const) | deferred 1 — pre-existing, not introduced by story |
| 2 | reviewer-edge-hunter | Yes | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 1 valid, 1 false positive | deferred 1 — empty catch at line 241 is pre-existing; dismissed 1 — empty test bodies claim was false (15 expect() calls verified) |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Yes | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 7 | confirmed 0 (story-introduced), deferred 5 (pre-existing), dismissed 2 (test-only/low) |

**All received:** Yes (3 returned with results, 6 disabled via settings)
**Total findings:** 0 confirmed blocking, 2 dismissed (with rationale), 6 deferred (pre-existing)

### Rule Compliance

Rules checked against the story diff (2 files: 1 production line change, 1 new test file with 282 lines):

| Rule | Instances | Compliant | Notes |
|------|-----------|-----------|-------|
| 1. Type safety escapes | 0 in diff | N/A | The `as DashboardState["latestSnapshot"]` on line 140 is pre-existing — the diff only changes the string on line 139 |
| 2. Generic/interface | 1 (makeWatcherEvent `Record<string, unknown>`) | Yes | Uses `unknown` not `any` |
| 3. Enum anti-patterns | 0 | N/A | No enums in diff |
| 4. Null/undefined | 0 in diff | N/A | No new null handling introduced |
| 5. Module/declaration | 1 (test import) | Yes | Follows project convention (Vite bundler) |
| 6. React/JSX | 0 in diff | N/A | useEffect is pre-existing, not changed |
| 7. Async/Promise | 0 | N/A | No async code in diff |
| 8. Test quality | 6 tests, 15 assertions | Yes | No vacuous assertions; all `toEqual`, `toBeNull`, `toHaveLength`, `toBe` are load-bearing |
| 9. Build/config | 0 | N/A | No config changes |
| 10. Input validation | 0 in diff | N/A | JSON.parse cast is pre-existing |
| 11. Error handling | 0 in diff | N/A | Empty catch is pre-existing |
| 12. Performance/bundle | 0 | N/A | Named imports only |
| 13. Fix-introduced regressions | 1 (the string change) | Yes | No new type escapes, no new patterns. String change is correct. |
| A1. No silent fallbacks | 0 in diff | N/A | Pre-existing |
| A4. Wiring test | 1 (test suite) | Deferred | See Devil's Advocate — the hook→DashboardApp wiring is pre-existing and unchanged by this story |

### Devil's Advocate

Let me argue this code is broken.

**The stale comment is a trap.** Line 138 says "Extract snapshot from state transitions" but the code now matches `game_state_snapshot`. A future developer reading this comment will think the code processes `state_transition` events. If they need to add a second handler for actual `StateTransition` events (which is a real variant — lib.rs:90), the misleading comment could cause them to modify this block instead of adding a new one, breaking snapshot wiring. This is exactly the kind of comment-code drift that causes bugs in 6 months.

**The event type string is a magic string with no compile-time safety.** The entire root cause of this bug was a string mismatch between Rust's serde output and a TypeScript string literal. The fix replaces one magic string with another. There is no shared constant, no codegen, no TypeScript enum that maps to the Rust `WatcherEventType` variants. If someone adds a new variant or renames one in Rust, the same class of silent mismatch recurs. The `EVENT_TYPE_COLORS` map in `TurnRow.tsx` already demonstrates this — it has `state_transition` but not `game_state_snapshot`, meaning snapshot events get fallback coloring.

**What if the server sends both `state_transition` AND `game_state_snapshot`?** The `StateTransition` variant (lib.rs:90) is a separate, real event type for state machine transitions. Before this fix, the dashboard was accidentally listening for `state_transition` (which carries different fields — no `snapshot`). Now it correctly listens for `game_state_snapshot`. But nothing prevents a confused developer from emitting snapshot data on a `state_transition` event, which would be silently dropped. The negative test covers this case, which is good.

**The `as DashboardState["latestSnapshot"]` cast on line 140 is load-bearing for this exact feature.** If the server sends a malformed snapshot (wrong shape, missing fields), it becomes a typed `GameSnapshot` with no validation. The `StateTab` and `SnapshotTree` components will receive garbage and either crash or render nonsense. The fix makes this cast *reachable* where it was previously dead code. So while the cast is pre-existing, the fix activates it. A malformed snapshot now flows through to the UI where before it was silently filtered out by the wrong event type.

**The reconnect race in the cleanup path means a dashboard that unmounts during WebSocket reconnection will leak a timer and potentially dispatch to an unmounted component.** React 18+ strict mode double-mounts in dev, which would trigger this path regularly. However — this is pre-existing and not changed by this story.

**Verdict after devil's advocate:** The stale comment is a real (low) concern but not blocking. The magic string problem is the actual systemic issue but is out of scope for a 2-point bug fix — it's an architectural observation for future work. The activated cast is worth noting but the existing guard (`event.fields.snapshot` truthiness check) provides a minimal safety net. None of these rise to Critical or High for the **code introduced by this story**.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** WebSocket message → `JSON.parse` → `processEvent` → `event.event_type === "game_state_snapshot"` match at useDashboardSocket.ts:139 → `updatedTurn.snapshot` assigned → `latestSnapshot` propagated at line 185 → returned from `useDashboardSocket()` → consumed by `DashboardApp` → passed to `StateTab` via `state.turns` and `PersistenceTab` via `state.latestSnapshot`. Safe because the event type now matches the API's serde serialization of `WatcherEventType::GameStateSnapshot` (confirmed at sidequest-api lib.rs:74,94 — `#[serde(rename_all = "snake_case")]`).

**Wiring verified:**
- [VERIFIED] API emits `WatcherEventType::GameStateSnapshot` with `fields.snapshot` and `fields.turn_number` — evidence: dispatch/mod.rs:1461-1472. Serde `snake_case` rename confirmed at lib.rs:74.
- [VERIFIED] Dashboard listener matches `"game_state_snapshot"` — evidence: useDashboardSocket.ts:139 (the fix). Matches API serialization.
- [VERIFIED] `useDashboardSocket` hook is imported and called in production code — evidence: DashboardApp.tsx imports and calls it (confirmed by rule-checker A3 check). Non-test consumer exists.
- [VERIFIED] `StateTab` receives turns with snapshot data — evidence: DashboardLayout.tsx:79 passes `state.turns` to `StateTab`.
- [VERIFIED] `latestSnapshot` propagated — evidence: useDashboardSocket.ts:185 `const latestSnapshot = updatedTurn.snapshot ?? state.latestSnapshot`.

**Pattern observed:** [VERIFIED] Correct use of `findOrCreateTurn` for turn correlation — useDashboardSocket.ts:84. Snapshot events correlate to existing turns by `turn_number` without creating duplicates. `previousSnapshot` chains correctly via findOrCreateTurn:36-37.

**Error handling:** [VERIFIED] Guard at line 139 checks both `event.event_type === "game_state_snapshot"` AND `event.fields.snapshot` truthiness before assignment. Events without a snapshot field are correctly ignored — confirmed by passing test "ignores game_state_snapshot without snapshot field".

**Security:** No auth, tenant isolation, or user input concerns — this is a GM-only dashboard consuming internal telemetry events over a watcher WebSocket. No user-facing input paths.

**Tests:** 6/6 passing. Tests cover AC-1 (snapshot population), AC-1 negative (wrong event type rejected), AC-3 (previousSnapshot chaining for diff view), AC-4 (turn correlation without duplicates), and edge case (missing snapshot field). All assertions are non-vacuous (15 expect() calls with toEqual, toBeNull, toHaveLength, toBe).

**Subagent findings incorporated:**
- [SILENT] Empty catch at useDashboardSocket.ts:241 — pre-existing, deferred. Not introduced by this story.
- [RULE] 5 pre-existing violations (type casts, reconnect race, JSON.parse without validation, empty catch) — all deferred as out of scope for this 2-point bug fix.
- [RULE] makeWatcherEvent untyped return in test — dismissed: test-only, low severity, factory produces structurally valid events that round-trip through JSON.parse.
- [RULE] Missing wiring test (A4) — deferred: the hook→DashboardApp import is pre-existing and unchanged. The 6 unit tests thoroughly cover the reducer behavior that this story modifies.
- [EDGE] Disabled via settings — N/A.
- [TEST] Disabled via settings — N/A.
- [DOC] Disabled via settings — N/A.
- [TYPE] Disabled via settings — N/A.
- [SEC] Disabled via settings — N/A.
- [SIMPLE] Disabled via settings — N/A.

**Observations:**
1. [LOW] Stale comment at useDashboardSocket.ts:138 — says "state transitions" but code matches `game_state_snapshot`. Should read "Extract snapshot from game state snapshot events".
2. [LOW] Missing `game_state_snapshot` color entry in TurnRow.tsx:15-23 `EVENT_TYPE_COLORS` map — snapshot events use fallback color in timeline. Pre-existing gap, not introduced.
3. [VERIFIED] Negative test correctly guards against regression — test "does NOT populate snapshot from state_transition events" ensures the old broken string never re-enters.
4. [VERIFIED] 6/6 story tests green, 0 new test failures introduced — preflight confirmed.
5. [VERIFIED] The `as DashboardState["latestSnapshot"]` cast at line 140 is guarded by the truthiness check on `event.fields.snapshot` at line 139 — prevents null/undefined assignment. Pre-existing cast, not introduced.

**Handoff:** To Grand Admiral Thrawn (SM) for finish-story

## Delivery Findings

### TEA (test design)
- No upstream findings during test design.

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- **Improvement** (non-blocking): Stale comment at useDashboardSocket.ts:138 says "state transitions" but code matches `game_state_snapshot`. Affects `sidequest-ui/src/components/Dashboard/hooks/useDashboardSocket.ts` (update comment text). *Found by Reviewer during code review.*
- **Gap** (non-blocking): `EVENT_TYPE_COLORS` map in TurnRow.tsx missing entry for `game_state_snapshot` — snapshot events use fallback color in timeline. Affects `sidequest-ui/src/components/Dashboard/tabs/Timeline/TurnRow.tsx` (add color entry). *Found by Reviewer during code review.*

## Design Deviations

### TEA (test design)
- **AC-2 and AC-5 not unit-tested**
  - Spec source: context-story-18-2.md, AC-2 and AC-5
  - Spec text: "Tree view navigable" and "Console tab confirms"
  - Implementation: No unit tests written for these ACs
  - Rationale: AC-2 tests UI rendering behavior (expandable tree) which is a StateTab component concern, not a reducer concern. AC-5 is observational — raw events already flow to Console tab regardless of this bug. Neither AC relates to the event type mismatch being fixed.
  - Severity: minor
  - Forward impact: none

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- **AC-2 and AC-5 not unit-tested** → ✓ ACCEPTED by Reviewer: agrees with TEA reasoning — AC-2 is a StateTab rendering concern and AC-5 is observational. The event type fix is the only behavior change; both ACs are satisfied by pre-existing UI code once snapshots flow correctly.