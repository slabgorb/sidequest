---
story_id: "73-9"
jira_key: ""
epic: ""
workflow: "trivial"
---
# Story 73-9: beat-impact descriptor test-coverage hardening — characterization tests for existing 73-4 behavior the suite left unpinned: backfire impact field asserts (tag/summary/dial_moved, not just effect), opponent>0 setback summary path (brace CritFail), same-side overwrite invariant (second player beat replaces first), encounter_resolved skip path (impact=None, no stamp), UI explicit-null render guard + inert-summary text render; drop the 2 redundant bare-truthy asserts (test_beat_impact.py:105, test_beat_impact_payload_wiring.py:92)

## Story Details
- **ID:** 73-9
- **Jira Key:** (none)
- **Workflow:** trivial
- **Stack Parent:** none
- **Points:** 2
- **Type:** chore
- **Status:** in_progress

## Overview

This story adds characterization tests to pin down existing beat-impact behavior (from 73-4/73-7/73-8) that the current test suite left unexercised. **No production code changes.** The goal is to make the behavior legible to future refactors and catch regressions.

The engine code shipped by 73-4, 73-7, and 73-8 is solid and has been playing. But the test suite has gaps:

- Backfire impact descriptors are only tested for the `effect` field; the full field set (tag, summary, dial_moved) is unpinned.
- Opponent >0 setback path (uncommon: opponent fumbles, recovers with a crit, net effect still forward) has no test.
- Same-side overwrite invariant (second player beat replaces first in last_beat_impacts) is undocumented.
- Encounter-resolved skip path (impact=None, no stamp) is untested.
- UI explicit-null render guard (BeatImpactPanel with null player impact but valid opponent impact) is unvalidated.
- Inert-summary text render in the UI is unvalidated.
- Two redundant bare-truthy asserts should be replaced with meaningful field asserts, not deleted.

## Technical Approach

### Server Test Coverage

**File: `sidequest-server/tests/server/test_beat_impact.py`**

1. **Backfire impact field asserts** — Add a test case that exercises a backfire impact (beat resolves, effect is negative/inert). Assert all four fields: `tag` (should be "backfire"), `summary` (human-readable), `dial_moved` (False/0), and `effect`.

2. **Opponent >0 setback summary path** — Add a test where the opponent takes a setback that advances the opponent's dial (opponent fumbles, recovers with a crit, net effect still forward). Verify the impact descriptor correctly encodes this as a setback with summary text reflecting the brace/recovery context. This pins the "opponent >0 setback" branch in `describe_beat_impact`.

3. **Same-side overwrite invariant** — Add a test where two player-side beats execute in sequence. Verify that `encounter.last_beat_impacts['player']` contains only the **second beat's impact**, not a list or merge. This ensures the invariant: "second player beat replaces first in the same-side slot."

**File: `sidequest-server/tests/server/test_beat_impact_payload_wiring.py`**

4. **Encounter-resolved skip path** — Add a test where a turn/beat resolves the confrontation but generates an impact with `impact=None` (no state change to render). Verify:
   - No `last_beat_impacts` entry is written (or it's explicitly None).
   - No watcher `beat_impact` span is emitted (or it's a no-op).
   - The encounter correctly transitions to `resolved=True`.

5. **Replace bare-truthy asserts** — Locate and replace the redundant bare-truthy asserts at lines 105 and 92 (or their current locations) with meaningful field asserts from AC-1 through AC-4. Do not just delete them; fold them into the new tests above.

### UI Test Coverage

**File: Component tests (ConfrontationOverlay or BeatImpactPanel in `sidequest-ui/src/__tests__/components/`)**

6. **Explicit-null render guard** — Add a test that passes a `last_beat_impact` payload with `player_beat_impact: null` and `opponent_beat_impact: { ... valid impact ... }`. Verify BeatImpactPanel renders without crash and displays the opponent's impact. Verify the panel does NOT render an empty/malformed player section.

7. **Inert-summary text render** — Add a test that exercises the inert/setback summary text in BeatImpactPanel. Verify the summary renders as intended (not `[object Object]`, not empty, legible). This pins the text-rendering path for zero-effect impacts.

## Acceptance Criteria Checklist

- [ ] Test 1: Backfire impact asserts full field set (tag/summary/dial_moved/effect)
- [ ] Test 2: Opponent >0 setback summary path with CritFail brace
- [ ] Test 3: Same-side overwrite invariant (second player beat replaces first)
- [ ] Test 4: Encounter-resolved skip path (impact=None, no stamp)
- [ ] Test 5: UI explicit-null render guard (player=null, opponent=valid)
- [ ] Test 6: UI inert-summary text render (legible output)
- [ ] Cleanup: Replace bare-truthy asserts with meaningful field asserts

## Workflow Tracking

**Workflow:** trivial
**Phase:** setup
**Phase Started:** 2026-06-04T06:44:26Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T06:44:26Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

No upstream findings at setup.

### TEA (implement / 73-9)
- **Gap (non-blocking) — confirms 73-13:** AC5 asks the UI to "display the opponent's impact" when the player impact is null. CURRENT code does NOT: `ConfrontationOverlay` gates the whole panel on `data.last_beat_impact` (line 733: `{data.last_beat_impact && <BeatImpactPanel…>}`), so a null player impact drops the opponent readout entirely. I characterized the SHIPPING behavior (no crash, panel gated off) per "no production change", and flagged that surfacing the opponent half when the player half is null is a real production change = the 73-13 bug. Same render-gate edge I noted in 73-7 verify ("unreachable in normal play" — but reachable if a payload ever carries opponent-only).
- **Improvement (non-blocking) — AC1 wording:** the session/context AC1 says backfire `tag` "should be 'backfire'". Real behavior: `effect='backfire'`, `tag='Off-Balance'` (the angle's own target tag). Tests pin reality; noted inline in the test.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

None at setup.

## Reviewer Assessment

**Verdict:** APPROVED (test-only story; no Critical/High; findings nit-level only)

**Scope reviewed:** Full branch diff vs develop in BOTH repos. Server `test_beat_impact.py` (+3 chars, +1 truthy-replacement) and `test_beat_impact_payload_wiring.py` (+1 char, +1 truthy-replacement); UI `ConfrontationOverlay.beatimpact.coverage.test.tsx` (+3 chars). **ZERO production change** — `git diff develop --name-only | grep -v tests` is empty in both repos; production component byte-identical to develop, so no regression surface.

**Tests (run by Reviewer, not trusted from handoff):**
- Server `-n0`: test_beat_impact.py 19/19 + test_beat_impact_payload_wiring.py 7/7 = **26/26 PASS** (0.12s).
- UI: coverage file 3/3; ConfrontationOverlay.test.tsx 41/41 → **44/44 PASS** (1.04s). (Broader 4-file sweep unnecessary here — no production delta to regress.)

**Verdicts on review focus 1–5:**
1. **Meaningful, not vacuous — CONFIRMED.** Every new assert pins a specific real value, and the fixtures drive the REAL `apply_beat`/`describe_beat_impact`/`ConfrontationOverlay` (no stubs). Standouts: `test_brace_critfail_is_opponent_setback` guards its own fixture (`assert deltas.opponent == 1`) before pinning the opponent>0 setback branch — so it can't silently become a zero-delta tautology; `test_angle_critfail_backfire_full_field_set` pins the whole descriptor (effect/dial_moved/own/opponent/resolution/tag/summary substrings). AC4 monkeypatches only the watcher sink — `apply_beat` itself runs for real.
2. **Truthy-replacements strengthen, no coverage lost — CONFIRMED (both files).** `assert impact.summary` (bare non-empty) → `assert impact.own == 0` + `assert impact.opponent == 0` (note: two separate asserts in the real diff, not the `&` footgun). The summary-content asserts (`"resolv" in …`, `"no dial"/"by design"`, `"broken" not in`) REMAIN — those already prove non-emptiness AND content, strictly stronger than the old bare-truthy. Net gain: numeric specificity added, prose coverage retained.
3. **AC3 + AC4 pin regression-catching invariants — CONFIRMED.** AC3 (`test_same_side_beat_overwrites_prior_impact`): `isinstance(stamped, dict)` + `effect=="tag"` (the 2nd beat) + `keys == ["player"]` — would fail loudly if anyone changed `last_beat_impacts` to a list/append-history. AC4 (`test_resolved_encounter_skips_impact_and_writes_no_stamp`): `impact is None` + `skipped_reason=="encounter_resolved"` + no player stamp + `emitted == []` — catches removal of the resolved-skip (the no-phantom-impact-after-fight-ends guard) AND a spurious watcher emit. Both are genuine tripwires, not decoration.
4. **Pin-reality + defer-to-73-13 — CORRECT (confirm).** A characterization story must pin SHIPPING behavior, not force a production fix — demanding an AC5 render-gate fix here would be scope creep that violates the trivial workflow's no-production-change intent. The render-gate gap is real (it is the SAME edge I independently flagged in 73-7 verify note #4) and is correctly owned by 73-13; AC1's "tag should be 'backfire'" wording mismatch (reality: `effect='backfire'`, `tag='Off-Balance'`) is pinned to reality and noted inline. Both gaps are logged in Delivery Findings with the right urgency. Exactly the right call.
5. **Zero production change — CONFIRMED** (see Scope).

**Deviation audit:** None logged; none needed (test-only). Delivery Findings (2 non-blocking, both → 73-13 / wording) are accurate and well-scoped.

**Findings:** 0 critical / 0 high / 0 medium / 1 nit.
- *Nit (placement):* `test_resolved_encounter_skips_impact_and_writes_no_stamp` lives in `test_beat_impact_payload_wiring.py` but characterizes `apply_beat` (not `build_confrontation_payload`); it would read more naturally beside its sibling in `test_beat_impact.py`. Harmless — both import `apply_beat`, the assertions are correct. Leave as-is.

**Observations (5+):**
1. Zero production change verified by name-only diff in both repos — the cleanest possible "no regression surface". ✓
2. Fixture-guard pattern (`assert deltas.opponent == 1`) prevents the opponent-setback test from degrading into a vacuous zero-check. ✓
3. Truthy-replacements keep the existing summary substring asserts → non-emptiness coverage not lost. ✓
4. AC4 over-mocking check: only `_watcher_publish` is monkeypatched; `apply_beat` runs real → the skip-path assertion is genuine. ✓
5. UI AC6 guards against the `[object Object]` / empty-render failure mode (asserts the actual summary string), and the inert own-delta=0 test guards the 73-7 numeric path for a zero value. ✓
6. TEA's 73-13 cross-reference matches my own 73-7 finding — the team is tracking the render-gate bug consistently across stories. ✓

**Handoff:** To SM for finish-story.
