# Context: 108-6 — WWN Dying Window + Solo-Actuator Gap

## Summary

Under a WWN binding, implement a real WWN dying window (mortally-wounded → d6-round stabilize → dead) that a downed solo PC drives by hand through free-text submissions, instead of going terminal-dead only. Resolves the solo-actuator gap: the clock is ticked by the player's own submissions; an engine-owned mechanism tracks elapsed rounds and fires expiry on the deadline. One input-gate carve lets the stabilizable window permit the submission; a branch in the downed seam routes to window vs terminal based on live-hostile presence.

## Architecture Overview

**State Machine:** Sequential, single-status (never dual-status #846 contradiction). Down event branches:
- **Live hostile remains** → terminal-dead immediately (no last stand at sword-point)
- **No live hostile** (scoped solo case) → mortally-wounded status minted with `incapacitating=True` + `stabilizable=True`

**Player-Driven Loop:**
1. PC drops to 0 HP with no live hostile → window status created, `dying_window.opened` emitted
2. Downed player submits free-text action (gate carves: stabilizable permits, terminal blocks)
3. Narrator resolves the attempt; if it's a stabilization, calls `stabilize_mortal_injury`
4. Post-resolution pass ticks the clock, checks expiry, emits `dying_window.tick` / `dying_window.resolved`
5. On deadline with no successful stabilize → window expires to terminal-dead

**Clock Ownership:**
- Engine-derived: `rounds_elapsed = current_round − created_turn` (from Mortal Injury status provenance #846)
- Narrator arg validated: supplied `rounds_elapsed` cross-checked against derived, fail-loud on mismatch
- Difficulty climbs: `8 + rounds_elapsed` — no anti-abuse mechanics beyond the fixed deadline

## Key Files

### Core Infrastructure (Already Exist)
- `sidequest/game/status.py` — Status model with `incapacitating` field; add `stabilizable: bool = False`
- `sidequest/game/ruleset/without_number.py` — `WithoutNumberRulesetModule.resolve_downed()` mints Mortal Injury
- `sidequest/agents/tools/stabilize_mortal_injury.py` — Existing Heal check + status clear; needs engine-owned clock + HP-to-1 fix
- `sidequest/server/dispatch/downed_seam.py` — Down event branch point; add live-hostile check + window branch
- `sidequest/handlers/player_action.py:534–589` — Turn-intake gate; carve for stabilizable window permit
- `sidequest/server/post_resolution_lethality.py` — Post-turn lethality pass; add expiry check + tick span

### New in This Story
- `sidequest/telemetry/spans/wn.py` — Three new emitters (`dying_window.{opened,tick,resolved}`); fold #846 `superseded_by_terminal` into mortal-injury extract
- `sidequest/game/ruleset/without_number.py:is_dying_window_status()` — Predicate keyed on `stabilizable` flag (not text scrape)
- Tests: 8 task-level tests + 1 end-to-end integration test

## Acceptance Criteria

**AC1:** Under a WWN binding, a solo PC dropped to 0 HP with NO live hostile enters the WWN dying window (one coherent status — never the #846 dual-status); a PC downed with a live hostile present still goes terminal immediately.

**AC2:** The downed soloist can submit free-text actions (input gate carve: stabilizable window permits+routes to narrator; terminal blocks).

**AC3:** The stabilize clock is engine-owned — rounds_elapsed derived from created_turn provenance (narrator-supplied value is a fail-loud cross-check); difficulty = 8 + rounds_elapsed; successful stabilize restores HP to 1 + Frail.

**AC4:** Expiry fires per-turn even on non-stabilization turns; clock cannot be paused; expiry converts window to terminal-dead.

**AC5:** Three OTEL spans (wwn.dying_window.opened/tick/resolved) + folded #846 superseded_by_terminal attribute on mortal_injury.declared extract.

**AC6:** Mandatory end-to-end solo wiring test proving gate→tick→both outcomes (stabilize lives, stall dies).

## Doctrine & Constraints

**ADR-143 (WN binding replaces native combat):** This story implements plain WWN SRD truth (dying window is a standard mechanic), not a native-vs-WN balance knob. No native beat mechanics are converted, tuned, or gated. The only new behavior is the input-gate carve (a single auditable point) and the branch in the down seam (standard conditional on live-hostile presence).

**ADR-114 (Ablative HP):** The dying window is built on existing Mortal Injury infrastructure; ablative HP lethality path is unchanged.

**CLAUDE.md (No Silent Fallbacks, Structured Markers, Lie-Detector):**
- Structured flag (`stabilizable`) for gate discrimination, never text scrape
- Engine-owned clock derived from provenance, narrator arg is fail-loud cross-check, not authority
- Three OTEL spans make every decision auditable to the GM panel (the lie-detector)

## Dependencies

**Blocks:** 108-7 (WN combat action surface buttons) — action buttons fire WN rolls; this story proves the dying-window free-text path works, creating the asymmetric contrast.

**Blocked By:** None. Depends only on existing infrastructure (#846 `created_turn` provenance, existing Mortal Injury, existing post-resolution lethality shape).

## Implementation Plan

**Workflow:** spdd (test-driven, superpowers-attested). 8 tasks structured test-first → implementation → commit:

1. **Status.stabilizable** structured field (unit)
2. **OTEL spans** (unit) + fold #846 `superseded_by_terminal`
3. **Window status flags** (`incapacitating` + `stabilizable`) + predicate (unit)
4. **Downed seam branch** (live-hostile → terminal vs window) (unit + integration)
5. **Input-gate carve** (terminal blocks, stabilizable permits) (unit)
6. **Engine-owned clock** + HP-to-1 fix (unit)
7. **Per-turn expiry** + tick/resolved spans (unit)
8. **End-to-end wiring test** (integration — drives real `player_action` gate through both outcomes)

Each task includes failing test → implementation → commit. Task 8 is the mandatory integration test that proves the loop turns on a real session.

## Refs

- **Design spec:** `docs/superpowers/specs/2026-06-14-wwn-dying-window-solo-actuator-design.md`
- **Implementation plan:** `docs/superpowers/plans/2026-06-14-wwn-dying-window-solo-actuator.md`
- **ADR-114:** Ablative HP Substrate
- **ADR-143:** A Without-Number Binding Replaces the Native Combat Engine
- **ADR-123:** Mechanical-Engagement Pipeline (LethalityArbiter)
- **Server #846:** Dual-status contradiction fix (dual-status → single Mortal Injury status, `created_turn` provenance)
- **GM Decisions:** 2026-06-13/14 ruling (gm-decisions.md)
- **Cancelled 106-5:** This story re-homes the dying-window work (cancellation commit `e5ae1fc8`)

## Brainstorm History

**2026-06-14 Brainstorm: COMPLETE**

Five sections of Approach A approved:
1. **Down-state machine:** Sequential, live-hostile branch, single status invariant
2. **Input-lane carve:** Free-text permitted through gate; narrator adjudicates actions
3. **Clock advancement:** Engine-derived `rounds_elapsed`, narrator arg fail-loud cross-check
4. **OTEL:** Three spans + #846 fold for GM panel auditability
5. **Test strategy:** Task-level tests + mandatory end-to-end wiring test

Open design problem (solo-actuator gap) resolved: player's own submissions tick the clock.
