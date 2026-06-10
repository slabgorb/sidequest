---
parent: context-epic-102.md
workflow: tdd
---

# Story 102-1: PC-death runs the WN downed seam

## Business Context

The combat half of the 90-3 AC5b proof ("WN lethality engaged, visible on the GM panel, in live play") cannot pass today: when the **player** is dropped, the engine emits only generic spans. In the 2026-06-10 long_foundry playtest, PC Vesska could die and the GM panel would show `hp_depletion.resolved` + `post_resolution_lethality.applied` — indistinguishable from a non-WN genre. For the mechanics-first players (Sebastien, Jade) the WN lethality stack (Shock, Mortal Injury) IS the crunch they asked for; for Keith-as-dev, a missing `wwn.*` span on a PC death means the lie detector can't tell whether WN lethality engaged or the narrator improvised. This is a P1 AC5b blocker.

## Technical Guardrails

- **The asymmetry is documented in-code.** `sidequest/server/post_resolution_lethality.py`'s docstring already names the root cause: `_resolve_opponent_reprisal` (`server/dispatch/dice.py:1057`) ablates the PC to 0 HP and resolves via `check_hp_depletion`, but — unlike the player-strike path which runs `run_cwn_wwn_downed_seam` after dropping a *defender* (`dice.py:760`) — applies no WN mechanical consequence to the *player*. Extend `post_resolution_lethality.py` (or its call site) to run the WN downed surface for the PC; do not fork a second lethality path.
- **Reuse `run_cwn_wwn_downed_seam`** (`server/dispatch/downed_seam.py`) or the module-level surface it wraps. The seam already knows how to emit `{ruleset}.mortal_injury`/`.shock` with the honest module slug. If the seam's signature assumes "defender = opponent," generalize the parameter, don't duplicate the body.
- **Respect the existing post-resolution contract:** the genre `lethality_policy.verdicts_on_zero_hp.pc` verdict, the Recovering/Downed status application, the `IncapacitationEvent` return, and idempotency (status tagged `created_in_encounter`) must all keep working exactly as today. The WN seam is **additive** on top of the verdict, not a replacement.
- **Span shape:** `{ruleset}.mortal_injury` / `{ruleset}.shock` with the binding module's slug (`wwn` for heavy_metal, `cwn`/`awn` likewise) — never hardcode `wwn.`.
- **Module gating:** non-WN genres (native ruleset) through this path must be a no-op — gate on the module capability (`isinstance` per the AWN subclass pattern), not on genre name.
- Per project memory: full parallel `tests/server/` runs deadlock ~18 OTEL span-count tests — run affected test files serially with `-n0`.

## Scope Boundaries

**In scope:**
- WN downed-seam execution on the opponent-drops-player path (reprisal → `check_hp_depletion` → `post_resolution_lethality`)
- OTEL span assertion test + a reprisal-lethal deterministic fixture (mirror `combat_wwn_emberfront`, 90-7)
- A wiring test proving the new path is reachable from production dispatch (per CLAUDE.md "Every Test Suite Needs a Wiring Test")

**Out of scope:**
- ADR-114 Part 2 death-clock ticking (explicitly future per the module docstring)
- The cast-path gaps (102-2, 102-3)
- Turn-model / initiative changes (102-4)
- UI death-banner changes — `CHARACTER_INCAPACITATED` surface already exists

## AC Context

1. **Dying PC emits WN lethality spans.** When opponent reprisal drops the PC to 0 in a WN-bound genre, the span stream contains `{ruleset}.mortal_injury` and/or `{ruleset}.shock` (per the module's lethality rules) alongside the existing `encounter.post_resolution_lethality`. Test: reprisal-lethal fixture, assert span presence + attributes (slug, verdict).
   - Edge: non-lethal verdict (`defeated`/`captured`/...) — does the WN seam still fire Shock-but-not-Mortal-Injury? Follow the module's own rules; assert both verdict branches.
   - Edge: native-ruleset genre through the same path emits NO `{ruleset}.*` WN spans (negative assertion).
2. **Existing behavior preserved.** Verdict application, recovery floor, Downed/Scar status, `IncapacitationEvent`, and idempotency are unchanged — existing `post_resolution_lethality` tests stay green.
3. **Wiring proof.** An integration test drives the full dispatch path (`dispatch_dice_throw` → reprisal → lethality) rather than calling the seam function directly.

## Assumptions

- The downed-seam function can accept a PC as the dropped party with modest signature generalization (if it can't, that's an early Architect flag, not silent rework).
- The reprisal-lethal scenario is reachable deterministically via the scene-harness/fixture machinery used by 90-7's `combat_wwn_emberfront`.
- E2E note (project memory): encounter creation is router-driven post-ADR-113; PC beats go via DICE_THROW, and the intent-router pass must be stubbed in e2e tests or they flake.
