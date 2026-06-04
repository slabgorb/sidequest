# Story Context: 73-8 — hp_depletion beat-impact reads the HP channel, not nominal suppressed dial deltas

> Recovered by SM (Camina Drummer) after a recurring sm-setup gap left the standalone
> context file unwritten. Derived from `.session/73-8-session.md` Technical Context (which
> carried the full ACs; TEA built RED from it). Epic 73 — Confrontation Engine Hardening.

- **Story:** 73-8
- **Epic:** 73 (Confrontation Engine Hardening)
- **Workflow:** tdd
- **Points:** 2
- **Repos:** sidequest-server (server-only — under hp_depletion the UI renders HP bars, not the dial-impact panel, so there is no UI surface; the value is GM-panel/OTEL consistency)
- **Stack parent:** 73-7 (opponent_last_beat_impact surface in confrontation payload)
- **Design context:** ADR-114 (Ablative HP Substrate — HP reclaims the lethality track beneath the dials)

## The Problem

Under `win_condition=hp_depletion` (SWN-style combat, ADR-114) the engine has two layers:
1. **Dial layer** (narrative pacing): momentum/leverage/engagement_range metric dials; strike/brace/angle/push beats — *how the confrontation moves this round*.
2. **HP layer** (lethality substrate): ablative HP, the concrete lethality track beneath the dials.

The engine separates them by design: `apply_beat` **suppresses dial application** for hp_depletion
encounters (beat_kinds.py ~564–583) and emits a `dial_suppressed_hp_depletion` watcher event;
the HP channel (`damage_channel=strike`, `damage_resolver`, `check_hp_depletion()`) is the
authoritative resolution track.

## The Bug

Despite suppressing the dial application, `describe_beat_impact()` still derives the impact from
the **nominal** dial deltas (call site ~line 549). So an SWN strike `Success` under hp_depletion
stamps `effect="advance"`, `dial_moved=True` — falsely reporting a dial move even though the dial
never moved on-screen (the move landed on HP). The GM panel then sees a beat readout that claims
the edge advanced while the HP bar/watcher shows HP changed instead — an inconsistency = the stamp
lies about the impact. A documented caveat from 73-4 sits at the stamp site (~lines 541–548).

## The Fix (mechanism left to Dev; contract is observable)

Make the stamped `last_beat_impacts` truthful under hp_depletion: a suppressed-dial beat must
stamp `dial_moved=False` and an effect that is NOT `advance`/`setback`. TEA's RED pins the
**observable boundary** (the stamp after a real `apply_beat`), so either mechanism satisfies it:
- **Option A (flag) — TEA's strong recommendation:** add `hp_depletion_suppressed: bool = False`
  to `describe_beat_impact`, pass `enc.win_condition == "hp_depletion"` at the call site, and under
  suppression drop the dial-motion precedence so strike/brace fall through to `inert` while
  tag/resolution still fire. Keep `inert` inside the existing closed `BeatEffect` union (a new
  `"suppressed"` literal would force a coordinated server+UI union change for a surface the UI
  doesn't render here).
- **Option B (recompute from HP):** couples the pure descriptor to encounter/HP state and
  order-of-operations — not recommended.

## Acceptance Criteria (TDD)

1. **describe_beat_impact under suppression:** strike Success, suppressed dials, no tag → `effect="inert"`, `dial_moved=False`, summary indicates suppression (no "to your edge"); strike with a granted tag still reports the tag (`effect="tag"`); push with resolution still reports `effect="resolution"` (resolution is never suppressed).
2. **Default (hp_depletion_suppressed=False / non-hp_depletion):** existing behavior unchanged — backwards-compatible default.
3. **Integration — apply_beat under hp_depletion:** fire a strike Success on an hp_depletion fixture; assert `last_beat_impacts["player"]["dial_moved"] is False`, `effect == "inert"`, and the HP channel recorded the actual damage (cross-channel consistency).
4. **OTEL truthfulness:** existing `dial_suppressed_hp_depletion` + `state_patch_hp` spans plus the corrected stamp are mutually consistent — watcher "dials suppressed", impact "inert", state_patch_hp "X damage" all agree. (No new span required — this corrects an existing stamp, not a new subsystem decision.)
5. **No regressions:** all beat_kinds + apply_beat tests pass; dial-threshold (non-hp_depletion) confrontations see no behavior change.

## RED status (TEA, commit 2441204)

`tests/game/test_hp_depletion_beat_impact_truthful.py` — 6 tests: 2 failing (the lie: `dial_moved`
asserted False, currently True), 4 green guards to keep green (`strike_fail_is_inert`,
`resolution_beat_still_resolves`, `dial_threshold_strike_success_still_advances`,
`describe_beat_impact_pure_dial_path_unchanged`). Non-blocking Dev note: under suppression the
stamped `own`/`opponent` numbers should likely be zeroed (73-7 surfaces them to the UI; a nominal
`own=2` alongside `dial_moved=False` is a latent inconsistency) — not pinned by RED.
