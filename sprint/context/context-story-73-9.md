# Story 73-9: Beat-Impact Descriptor Test-Coverage Hardening

## Status

**Epic:** 73 (Confrontation Engine Hardening)
**Type:** chore
**Points:** 2
**Workflow:** trivial
**Repos:** sidequest-server, sidequest-ui

## Objective

Add characterization tests to pin down existing 73-4/73-7/73-8 beat-impact behavior that the current test suite left unexercised. This is **test-coverage only** — no production code changes. The goal is to make the behavior legible to future refactors and catch regressions.

## Context

Stories 73-4 ("push/angle CritSuccess scores 0"), 73-7 ("opponent-side beat-impact legibility"), and 73-8 ("hp_depletion beat-impact truthfulness") ship beat-impact descriptor logic. The engine code is solid (shipped and playing), but the test suite has gaps:

1. **Backfire impact descriptors** are only tested for the `effect` field. The full field set (tag, summary, dial_moved) is unpinned.
2. **Opponent >0 setback path** (when opponent takes a setback that advances them, braced by CritFail) has no test.
3. **Same-side overwrite invariant** is undocumented: when two players act on the same confrontation turn, does the second beat's impact replace the first in `last_beat_impacts`?
4. **Encounter-resolved skip path** (impact=None, no stamp) is untested.
5. **UI explicit-null render guard** — BeatImpactPanel needs to handle a null player impact while opponent impact exists (73-13 bug).
6. **Inert-summary text render** in the UI is unvalidated.
7. **Redundant bare-truthy asserts** at test_beat_impact.py:105 and test_beat_impact_payload_wiring.py:92 should be replaced with the meaningful field asserts above, not just deleted.

## Acceptance Criteria

### Server: Backfire Impact Field Asserts
1. Add a test that exercises a **backfire impact** (beat resolves but effect is negative/inert).
2. Assert all four fields:
   - `tag` (should be "backfire")
   - `summary` (human-readable description of the backfire)
   - `dial_moved` (should be False or 0, depending on field type)
   - `effect` (should reflect the inert/negative nature)
3. File: `tests/server/test_beat_impact.py` (or new test class)

### Server: Opponent >0 Setback Summary Path
4. Add a test case where the **opponent** takes a **setback** that advances the opponent's dial (uncommon but valid: opponent fumbles, recovers with a crit, net effect is still forward).
5. Verify the impact descriptor correctly encodes this as a **setback** (not an advance/success), with summary text reflecting the brace/recovery context.
6. This pins the "opponent >0 setback" branch in `describe_beat_impact`.
7. File: `tests/server/test_beat_impact.py`

### Server: Same-Side Overwrite Invariant
8. Add a test where **two player-side beats execute in sequence** (e.g., two combatants acting in the same round).
9. Verify that `encounter.last_beat_impacts['player']` contains only the **second beat's impact**, not a list or merge.
10. This ensures the invariant: "second player beat replaces first in the same-side slot."
11. File: `tests/server/test_beat_impact.py` or `tests/server/test_confrontation_state.py`

### Server: Encounter-Resolved Skip Path
12. Add a test where a turn/beat resolves the confrontation but generates an impact with `impact=None` (no state change to render).
13. Verify:
    - No `last_beat_impacts` entry is written (or it's explicitly None).
    - No watcher `beat_impact` span is emitted (or it's a no-op).
    - The encounter correctly transitions to `resolved=True`.
14. File: `tests/server/test_beat_impact_payload_wiring.py`

### UI: Explicit-Null Render Guard
15. Add a test in the React test suite that passes a `last_beat_impact` payload with:
    - `player_beat_impact: null`
    - `opponent_beat_impact: { ... valid impact ... }`
16. Verify **BeatImpactPanel renders without crash** and displays the opponent's impact.
17. Verify the panel does NOT render an empty/malformed player section.
18. File: Component test for `ConfrontationOverlay` or `BeatImpactPanel`

### UI: Inert-Summary Text Render
19. Add a test that exercises the **inert/setback summary text** in BeatImpactPanel.
20. Verify the summary renders as intended (not `[object Object]`, not empty, legible).
21. This pins the text-rendering path for zero-effect impacts.
22. File: Component test

### Cleanup: Replace Redundant Bare-Truthy Asserts
23. **Locate lines:**
    - `tests/server/test_beat_impact.py` line 105
    - `tests/server/test_beat_impact_payload_wiring.py` line 92
24. **Do NOT just delete them.** Replace them with the meaningful field asserts from AC-1 and AC-2 above. If a bare-truthy assert was checking for "truthy" (non-None, non-False), replace it with an explicit field assertion (e.g., `assert impact.tag == "backfire"`).
25. Verify all six AC goals above are covered by the resulting test suite.

## Technical Approach

### Files to Modify (Test-Only)

**Server tests:**
- `sidequest-server/tests/server/test_beat_impact.py` — add backfire, setback, overwrite tests
- `sidequest-server/tests/server/test_beat_impact_payload_wiring.py` — add encounter_resolved skip path test, replace bare-truthy asserts

**UI tests:**
- `sidequest-ui/src/__tests__/components/ConfrontationOverlay.test.tsx` (or `BeatImpactPanel.test.tsx`) — add null-guard + summary-render tests

### No Production Code Changes

This story **does not ship any changes to:**
- `sidequest/game/confrontation.py` (engine already correct)
- `sidequest/game/beat_kinds.py` (descriptors already shipped)
- `sidequest/components/ConfrontationOverlay.tsx` (UI already ships the data; test validates render)

Any production-code gaps discovered during testing should be filed as a separate story (do not widen scope here).

## Related ADRs / Stories

- **73-4** — Beat-impact descriptor design (already shipped)
- **73-7** — Opponent-side legibility (already shipped, added last_beat_impacts dual-side tracking)
- **73-8** — HP-depletion truthfulness (already shipped, fixed descriptor derivation)
- **ADR-024** — Dual-dial encounter model (provides the scoring context)
- **ADR-074** — Dice resolution protocol (player-facing rolls)

## Testing Notes

- All tests use the existing `@pytest.fixture` ecosystem (`session_handler_factory`, etc.).
- No new fixtures are required (use the shared ones from `tests/conftest.py` as of 73-6).
- UI tests use React Testing Library and the existing test harness in `src/__tests__/`.
- Verify `just server-check` and `just client-test` pass after changes.

## Delivery Findings

(Agents append discoveries here as they work.)

No upstream findings at setup.

## Design Deviations

(Agents log spec deviations here, not after the fact.)

None yet.
