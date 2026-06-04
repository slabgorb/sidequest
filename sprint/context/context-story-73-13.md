# Story 73-13: BeatImpactPanel render-gate

## Story Details
- **ID:** 73-13
- **Type:** bug
- **Points:** 2
- **Repos:** sidequest-ui
- **Workflow:** tdd

## Summary
BeatImpactPanel render-gate drops opponent readout when player impact absent — ConfrontationOverlay gates the panel on `{data.last_beat_impact && ...}`, so in the opponent-acts-first window (legacy beat_selection path / surprise round / player takes a non-combat action: opponent impact present, player impact absent) the WHOLE panel is suppressed, hiding the "the enemy hit you" readout 73-7 added.

## Technical Approach

### Root Cause
The `ConfrontationOverlay` component gates the entire `BeatImpactPanel` on the presence of `data.last_beat_impact.player_impact`, which incorrectly suppresses the panel when only the opponent has an impact (opponent acts first, player hasn't yet acted).

### Solution
1. Relax the render gate to `(data.last_beat_impact && (data.last_beat_impact.player_impact || data.last_beat_impact.opponent_impact))`
2. Update `BeatImpactPanel` to gracefully handle the absence of `player_impact` (display opponent impact regardless)

### Acceptance Criteria
1. BeatImpactPanel renders when opponent has an impact, even if player impact is absent
2. Opponent readout ("the enemy hit you") is visible in opponent-acts-first window
3. No regression: panel still suppressed when no impacts exist at all
4. Player and opponent impacts display independently when present

## References
- Related: 73-7 (opponent readout added)
- Reviewer correction: narration_apply.py:4031-4055 preserves opponent-side selections; last_beat_impacts accumulates/never clears (not a data bug)
