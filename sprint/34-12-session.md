---
story_id: "34-12"
jira_key: "MSSCI-1034"
epic: "MSSCI-1034"
workflow: "trivial"
---

# Story 34-12: Playtest Validation — End-to-End Dice Rolling in Multiplayer Session

## Story Details

- **ID:** 34-12
- **Jira Key:** MSSCI-1034
- **Workflow:** trivial
- **Stack Parent:** none (independent playtest validation)
- **Points:** 2
- **Type:** chore

## Scope

This story surfaces end-to-end wiring bugs that unit tests in 34-5/34-6/34-7 missed. The failure Keith observed during playtest:
- **Symptom:** DC 14 check fires, DiceOverlay panel header visible, but **Three.js canvas is empty** (blank/no dice rendering)
- **Known-Good Reference Points:**
  - 34-5 merged: `src/dice/` directory + lazy-loaded overlay component
  - 34-6 merged: `useDiceThrowGesture` hook (drag-and-throw interaction)
  - 34-7 merged: seed-based Rapier replay (deterministic physics)
  - 34-8 merged: multiplayer broadcast via SharedGameSession
  - 34-9 merged: narrator outcome injection into narration tone
  - 34-11 merged: OTEL dice spans (request_sent, throw_received, result_broadcast)

## Workflow Tracking

**Workflow:** trivial
**Phase:** setup
**Phase Started:** 2026-04-13

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-13 | - | - |

## Diagnosis Focus — Read First

The wiring chain that must fire end-to-end:

1. **Backend:** Sealed letter turn → beat selection → `IntentRouter::select_beat()` emits `DiceRequest`
2. **Network:** `DiceRequest` broadcast over WebSocket to all clients via `SharedGameSession`
3. **Frontend:** `useGameSession()` receives `DiceRequest` → triggers `useDiceOverlay()` mount
4. **UI:** `DiceOverlay` component loads, renders Rapier canvas (Three.js scene)
5. **Interaction:** Player drags dice in canvas, fires `ThrowParams` via `useDiceThrowGesture()`
6. **Backend:** Server receives `DiceThrow` → computes `DiceResult` via `resolve_roll()`
7. **Broadcast:** `DiceResult` sent back → all clients render outcome + update game state
8. **Narration:** `RollOutcome` shapes narrator tone in next beat

**Suspected Break Points (Dev: trace these first):**
- Is `DiceRequest` arriving at the client? (Check OTEL logs in inspector, check WebSocket tab in DevTools)
- Is `useDiceOverlay()` hook being called when `DiceRequest` arrives?
- Is `DiceOverlay` component mounting? (Try adding a console.log at the top of the component)
- Is the Three.js canvas element being created in the DOM? (Check DevTools Elements tab)
- Is Rapier initialization succeeding? (Rapier might be failing silently)

## What Dev Should Do

**Phase: implement**

1. **Diagnosis (15 min):**
   - Run playtest again and capture DevTools logs (Network, Console, OTEL)
   - Look for `DiceRequest` in WebSocket stream
   - Check if `DiceOverlay` component is in the DOM
   - Verify Rapier canvas element exists (even if empty)

2. **Debug the Break Point (30 min):**
   - Add `console.error()` handlers to Rapier initialization
   - Check if `THREE.WebGLRenderer` is throwing silently
   - Verify canvas context is not null
   - Look for width/height mismatch or CSS hiding the canvas

3. **Fix & Re-Test (15 min):**
   - Apply fix to UI or API dispatch as needed
   - Re-run full playtest flow (sealed letter, check DC, throw dice, see resolution)
   - Verify OTEL spans complete: request_sent → throw_received → result_broadcast

## Delivery Findings

No upstream findings at setup. Dev will populate during diagnosis.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

None at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->
