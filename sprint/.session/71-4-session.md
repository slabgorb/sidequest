---
story_id: "71-4"
jira_key: null
epic: null
workflow: "tdd"
---

# Story 71-4: Player-action transcript — contrast bump on own-echo + persist peer action post-resolution

## Story Details
- **ID:** 71-4
- **Type:** Bug, 3 points
- **Workflow:** tdd
- **Repo:** sidequest-ui
- **Branch:** feat/71-4-player-action-transcript-contrast-persist

## Problem Statement

Two readability/persistence issues in the multiplayer action visibility subsystem (ADR-036, amended 2026-05-03):

1. **Contrast bump on own-echo**: When a player's own submitted action is echoed back into the narration transcript, the rendering contrast is too low (`text-muted-foreground/70`), making it hard to read. The own action should have higher contrast than peer actions to distinguish it from surrounding narration.

2. **Persist peer action post-resolution**: Peer players' action text (from `ACTION_REVEAL` messages during composition/submission) is currently shown only in the ephemeral `PeerRevealList` UI during the wait phase. Once a turn resolves, the `PeerRevealList` is cleared and peer actions vanish. Per ADR-036 doctrine (collaborative visibility by default), peer action text should be persisted into the main narration transcript/cards so the table can review what each player did after resolution.

## Acceptance Criteria

### AC1: Own-action contrast bump
- [ ] Player's own submitted `player-action` segment in the narrative transcript has visibly higher contrast than peer-contributed segments
- [ ] The CSS styling distinguishes own vs. peer actions (likely via a data attribute or CSS class on the player-action element)
- [ ] Contrast ratio passes WCAG AA accessibility standards (4.5:1 minimum for body text)

### AC2: Peer action persistence
- [ ] When a peer player submits an action (`ACTION_REVEAL` with `status="submitted"`), that action text is recorded and persisted
- [ ] After `TURN_STATUS{status="resolved"}`, the peer action entries appear in the narration card stream alongside or immediately after the turn's `player-action` segments
- [ ] Peer actions render with lower contrast than own actions (visual hierarchy: own > peer > prose)
- [ ] Test: multiplayer session with 2+ players, each player submits, verify both own and peer actions appear in scrollback post-resolution

## Technical Approach

### Part 1: Contrast Bump (Own-Action Styling)
1. Add a data attribute or CSS class to the `player-action` segment renderer to distinguish own vs. peer actions
2. Modify `narrativeRenderers.tsx` `renderSegment()` to accept an optional `isOwnAction` parameter
3. Pass `isOwnAction` from `NarrationCards` or segment builder — will need to wire player_id from state
4. Update CSS in `narrativeRenderers.tsx` or `archetype-chrome.css` to apply higher contrast for own actions (e.g., `text-foreground` instead of `text-muted-foreground/70`)

### Part 2: Peer Action Persistence
1. Extend the `NarrativeSegment` type to support a new `peer-action` kind (or reuse `player-action` with an `is_peer` flag)
2. Extend `buildSegments()` in `narrativeSegments.ts` to accept a `peerActionsMap` parameter (Map<player_id, ActionRevealEntry>)
3. When building segments from `messages`, inject peer action entries at the appropriate turn boundaries — likely immediately after the turn's primary `player-action` (own action), or grouped at turn end
4. Wire the peer reveals from `usePeerReveals` hook into the segment builder
   - Pass `peerReveals.reveals` from `GameBoard` → `NarrationCards` → `buildSegments()`
   - Trigger segment rebuild on peer reveals update (already happens via message flow, but ensure round/turn boundaries align)
5. Add tests:
   - Unit test in `narrativeSegments.ts` validating peer actions appear in the right turn
   - Integration test in action-reveal-wiring validating full end-to-end flow (send ACTION_REVEAL, verify it persists post-TURN_STATUS resolved)

## Implementation Notes

- **Player ID context**: The segment builder currently doesn't track player identity. Will need to pass `currentPlayerId` (or `selfPlayerId`) to `buildSegments()` to know which segments are own vs. peer.
- **Timing**: Peer reveals are ephemeral (cleared on round transition). The segment builder will need a snapshot of the peer reveals at turn resolution time, or we persist them separately.
- **Styling layer**: Both changes are in the rendering/CSS layer — no backend changes needed. Backend already emits ACTION_REVEAL with all necessary metadata.
- **PeerRevealList integration**: The PeerRevealList (currently above InputBar) shows composing/submitted state during the wait phase. This story is about moving that information into the persistent narration transcript post-resolution.

## Sm Assessment

Setup verified for peloton handoff to TEA (Radar O'Reilly) for the RED phase. Two-part UI bug in sidequest-ui, both in the render/CSS layer (no backend — ACTION_REVEAL already carries the metadata):
1. Contrast bump on own-action echo (readability — this is a player-facing surface; Alex the slower reader benefits from legible own-action echo).
2. Persist peer action text in the transcript post-resolution (extends ADR-036's 2026-05-03 collaborative-visibility amendment from wait-phase-only into the persistent narration).

**Routing notes for the team:**
- TEA leads RED — write failing tests for both ACs. Part 2 needs the segment-builder (narrativeSegments.ts buildSegments) to know own-vs-peer identity (currentPlayerId) and to snapshot peer reveals at turn-resolution time (they're ephemeral, cleared on round transition — that's the trap).
- MP / ADR-036 watch for Reviewer: peer-action persistence must respect perception filtering (ADR-104/105) — a peer's action text is only persisted if it was already visible per the collaborative-visibility rule; do NOT surface hidden/sealed actions. (Sealed-visibility is PvP-only and not implemented, but the firewall must not regress.)
- Wiring test required (project doctrine): full ACTION_REVEAL → persisted-segment flow through the real component, not just a buildSegments unit assert.
- Dev: the peer-reveal snapshot-at-resolution is the load-bearing design choice — coordinate with Architect if the ephemeral→persistent bridge needs a new state holder vs. deriving from message history.
- Architect on standby — ADR-036/104/105 perception implications make this worth a spec-check at green.

Branch off current develop (c8e0546, includes 71-3). A previous lane's uncommitted WIP (3 archetype-chrome CSS files) is in the shared checkout — do NOT stage/disturb. Clear to hand to TEA.

## Delivery Findings

### TEA (test design)
- **Question** (non-blocking): The wiring threads `peerActions: Map<round, ActionRevealEntry[]>` into the narration component. I inferred the prop name `peerActions` on `NarrationCards`. Dev should confirm the prop name and — critically — wire ALL THREE narration components (`NarrationScroll` is the production default per `NarrativeView`, plus `NarrationFocus`, `NarrationCards`), not just one. Affects `NarrativeView.tsx` + the three components. *Found by TEA during test design.*
- **Gap** (blocking for AC2): The snapshot-before-clear capture must be added to App's `TURN_STATUS{resolved}` handler (`App.tsx:792-799`) BEFORE `peerRevealsClearRef.current?.()` fires, and the resulting accumulator threaded App → GameBoard → NarrativeWidget → NarrativeView → narration component (5 hops). Partial wiring = half-feature; the e2e wiring test only passes when the full chain renders the persisted segment. *Found by TEA during test design.*
- **Question** (non-blocking): In MP, does the client receive peers' `PLAYER_ACTION` in `messages`, or only its own? The locked design assumes `messages` PLAYER_ACTION = own (is_peer absent) and peers arrive only via the accumulator. If peer PLAYER_ACTION frames also land in `messages`, own/peer detection needs `currentPlayerId` in buildSegments too. Dev/Architect to confirm. *Found by TEA during test design.*

## Design Deviations

### TEA (test design)
- **WCAG AA contrast asserted at token level, not computed ratio**
  - Spec source: 71-4 AC1 (contrast ratio passes WCAG AA 4.5:1)
  - Spec text: "Contrast ratio passes WCAG AA accessibility standards (4.5:1 minimum for body text)"
  - Implementation: Tests assert the high-contrast `text-foreground` token on own actions vs the `text-muted-foreground` token on peer actions; jsdom cannot compute rendered contrast ratios.
  - Rationale: jsdom has no layout/color engine; the token distinction is the testable proxy. Actual 4.5:1 verification is a Reviewer/manual concern.
  - Severity: minor
  - Forward impact: Reviewer should manually confirm the chosen foreground token meets 4.5:1 against the card background.
- **E2E wiring test mirrors App's capture in a Host harness**
  - Spec source: project wiring doctrine + SM Assessment routing note
  - Spec text: "full ACTION_REVEAL → persisted-segment flow through the real component"
  - Implementation: The wiring Host reproduces App's snapshot-before-clear handler (real `useGameSocket` + real `usePeerReveals` + real `NarrationCards`), rather than mounting all of `App`.
  - Rationale: App is too large to mount in a focused wiring test; the existing `action-reveal-wiring.test.tsx` established this Host-mirror pattern. The real socket, hook, and component are exercised; only the App glue is mirrored.
  - Severity: minor
  - Forward impact: Dev's actual App capture logic must match the Host's filter(submitted)+dedup(player_id,round) semantics; Reviewer should diff the two.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED — 6 failing (ready for Dev), 5 guards passing. Lint clean.

**Test Files:**
- `src/__tests__/player-action-transcript-71-4.test.tsx` — AC1 contrast + AC2 unit/firewall/focus
- `src/__tests__/peer-action-persistence-wiring-71-4.test.tsx` — AC2 end-to-end wiring

**RED (failing for the right reason):**
| Test | AC | Why RED |
|------|----|---------|
| own player-action higher contrast than muted default | AC1 | all actions use `text-muted-foreground/70` today |
| own vs peer distinct contrast classes | AC1 | own==peer today |
| buildSegments persists submitted peer reveal as is_peer segment | AC2 | buildSegments ignores 2nd param |
| peer action not a turn-page starter (buildTurnPages) | AC2 | peer player-action currently starts a new page |
| e2e: submitted peer action survives TURN_STATUS{resolved} | AC2 | persistence path unimplemented |
| e2e: dedup one-per-peer | AC2 | persistence path unimplemented |

**Guards (passing now, must keep passing):**
- AC1 peer player-action stays muted
- AC2 buildSegments firewall (entry absent from map → not rendered)
- AC2 single-player unchanged (no accumulator → no peer segs)
- AC2 component-boundary firewall (TURN_STATUS-borne action text never surfaces)
- AC2 e2e composing-only reveal does not persist

**Pinned to Architect ruling A1:** `buildSegments(messages, peerActions: Map<round, ActionRevealEntry[]>)`; peer actions reuse `player-action` kind + `is_peer:true`; own=is_peer absent (high contrast), peer=is_peer true (lower); placement at round turn boundary; peer action not a turn-page starter; snapshot at resolved filtered to submitted + deduped.

**Handoff:** To Dev for GREEN.