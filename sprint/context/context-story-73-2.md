---
parent: context-epic-73.md
workflow: tdd
---

# Story 73-2: trial withdraw/concede beat + opposed_check

**ID:** 73-2 · **Epic:** 73 (Confrontation Engine Hardening) · **Points:** 3 ·
**Workflow:** tdd · **Type:** bug · **Repos:** sidequest-content, sidequest-server

> Read the parent epic context first: `sprint/context/context-epic-73.md`. This
> story is the `trial` slice of the 59-8 generalization the epic describes.

## Business Context

**The core driver is a soft-lock — a player can get *stuck* mid-trial with no
way out.** The `trial` confrontation in the tea_and_murder pack
(`sidequest-content/genre_packs/tea_and_murder/rules.yaml`, `type: trial`,
lines ~206–251) has exactly four beats:

- `cross_examine` (`kind: strike`)
- `present_argument` (`kind: strike`)
- `object` (`kind: brace`)
- `yield` (`kind: angle`)

**None is a `push` and none carries `resolution: true`.** Resolution can fire
only when a conviction dial crosses its threshold (currently 8) — see
`sidequest/game/beat_kinds.py` lines 840–864, where the dial-threshold branches
and the `resolution`-flag branch are the *only* ways `enc.resolved` is set for a
dial confrontation. If neither side's conviction reaches threshold, there is **no
terminal beat the player can choose to end the scene.** The fiction may have
moved on (the player wants to withdraw the charge, accept a verdict, step down),
but the engine has no transition out. That is the same soft-lock class playtest
59-8 found and fixed for `social_duel`, and that `negotiation` was hardened
against defensively in 59-8's wake (`walk_away`, `resolution: true`). `trial` was
left behind.

This pack is tea_and_murder's primary mechanical surface — drawing-room social
confrontations are *the* crunch Sebastien and Jade (the group's two
mechanics-first players) came for, and the surface Keith and Jade, both
forever-GMs, run the Glenross line on. A confrontation a player cannot exit is a
table-killer: it forces a save-scum or a session abandon. The fix must make a
no-resolvable-beat `trial` **impossible by construction**.

**Two changes ship together** (mirroring the proven 59-8 `social_duel` recipe):

1. **Author a withdraw/concede beat** — a `push` beat with `resolution: true`
   that ALWAYS ends the trial regardless of the d20 outcome tier. This is the
   anti-soft-lock primitive.
2. **Convert `trial` to `resolution_mode: opposed_check`** — so the opponent
   (prosecution/tribunal) rolls its own d20+modifier each beat and its conviction
   dial advances mechanically, instead of freezing at 0 under the default
   `beat_selection` mode where only the player rolls. This makes the trial a real
   two-sided contest and gives the GM panel a real opposed roll to audit instead
   of narrator fiat (the same structural-fairness fix 59-8 applied to the duel).

## Technical Guardrails

### The reference pattern to copy — `social_duel.concede`

`social_duel` (same file, `type: social_duel`, lines ~303–378) is the worked
example. Copy its shape for `trial`:

- `resolution_mode: opposed_check` at the confrontation level.
- An `opponent_default_stats` block keyed by the stat names the beats'
  `stat_check` fields use. `trial`'s beats check `Cunning` (`cross_examine`,
  `object`) and `Passion` (`present_argument`, `yield`) — both stats must appear
  in `opponent_default_stats`, **and the new withdraw/concede beat's `stat_check`
  stat too.** `social_duel` uses `Humour: 10` for its `concede` beat; pick a
  declared stat for the trial exit and ensure it's in the block.
- **Every `opponent_default_stats` value ≤ 10** (ADR-093 parity ceiling — opponent
  challenge comes from dial/DC geometry, NOT stat inflation; 10 gives the +0
  modifier of a competent-but-fair adversary). `resolve_opponent_modifier`
  (`sidequest/game/opposed_check.py:159`) fails loud (`ValueError`, No Silent
  Fallbacks) if a beat's `stat_check` stat is missing from both the actor sheet
  and this block — so a missing stat is a crash, not a silent zero.
- `player_metric.threshold == opponent_metric.threshold == 7` — **lower the
  current `8` to `7`** per ADR-093 opposed_check calibration.
- A terminal `push` beat with `resolution: true` for the voluntary exit (the
  withdraw/concede beat). `social_duel.concede` is `kind: push`, `base: 0`,
  `resolution: true`, with a `consequence:` line.

### How `resolution: true` actually resolves

The flag is honored in `apply_beat` at `sidequest/game/beat_kinds.py:860`:

```python
elif not resolved and (deltas.resolution or getattr(beat, "resolution", False)):
    enc.resolved = True
    enc.outcome = f"resolution_beat:{beat.id}"
    enc.structured_phase = EncounterPhase.Resolution
```

This branch fires on **any** outcome tier — that is the entire point. A bare
`push` without the flag only resolves on Success/CritSuccess
(`DEFAULT_DELTAS[push]`), so a *failed* concede/withdraw roll would trap the
player. The `BeatDef.resolution` field (`sidequest/genre/models/rules.py:151`,
`resolution: bool | None`) is the declarative always-resolves override; authoring
`resolution: true` on the trial exit beat is the load-bearing line.

### The opposed_check path the conversion lights up

Once `trial` declares `resolution_mode: opposed_check`:

- `_requires_opponent` / `_is_adversarial` seating: `trial.category` is `social`,
  and per ADR-116's staged rollout the empty-opponent guard
  (`NoOpponentAvailableError`) is **not yet enforced for `social`**
  (`encounter_lifecycle.py`, `_ADVERSARIAL_CATEGORIES = {"combat", "movement"}`).
  But `_requires_opponent` folds `opposed_check` in for opponent-*seating* so the
  tribunal/prosecution Other gets `side="opponent"` and its dial can advance on
  its own roll (epic context §Technical Architecture). Do not change the
  ADR-116 staging in this story — seating an Other for opposed_check is existing
  behavior, not new work here.
- Resolution flows through `_resolve_opposed_check_branch`
  (`sidequest/server/narration_apply.py:4118`), which calls `resolve_opposed_check`
  (`opposed_check.py:206`) to derive one tier from the shift, emits
  `encounter.opposed_roll_resolved` (`encounter_opposed_roll_resolved_span`,
  `narration_apply.py:4472`) BEFORE applying beats, then calls `apply_beat` once
  per side. On resolution the pipeline fires `encounter_resolved_span`
  (`narration_apply.py:3367` / `:4775`).
- ADR-116 end-on-no-Other is already wired (`_resolve_if_no_opponent_remains`,
  `narration_apply.py:3485`) — the concede path's clean exit and any
  opponent-withdraw both land cleanly. This story does not modify that seam; it
  relies on it.

### Calibration guardrail — `trial` is now swept into the test

`tests/genre/test_confrontation_calibration.py` filters by **`resolution_mode`,
not type name**. Today its module docstring (lines 36–42) claims tea_and_murder
"is social-only by design (no opposed_check confrontations)" — **that comment is
stale**: `social_duel` is already `opposed_check` post-59-8, and this story makes
`trial` the second. The moment `trial` declares `opposed_check`:

- `test_opposed_check_thresholds_calibrated_to_7` will assert
  `trial.player_metric.threshold == trial.opponent_metric.threshold == 7` — this
  is why the `8 → 7` recalibration is mandatory, not optional.
- `test_opponent_default_stats_no_parity_12_remains` will assert every
  `trial` `opponent_default_stats` value is ≤ 10 (and never the legacy `12`).
  `hp`/`armor_class` are exempt (`OPPONENT_RESERVED_STAT_KEYS`,
  `sidequest/genre/models/rules.py`) but `trial` is a dial confrontation, not
  `hp_depletion`, so it should not carry those keys.

These parametrized rows currently pass trivially for tea_and_murder on the
`trial` entry; after conversion they become live assertions. **Both must stay
green.** Update the stale docstring claim about tea_and_murder being
opposed_check-free if it's misleading the next reader.

### Server-side test discipline

Per `sidequest-server/CLAUDE.md` "No Source-Text Wiring Tests": prove behavior
and wiring via **OTEL span assertions** and **fixture-driven behavior**, never by
grepping production source. For this story:

- Drive a synthetic `trial` encounter through the real `apply_beat` /
  `_resolve_opposed_check_branch` path and assert `enc.resolved is True` /
  `outcome` after the concede beat — do not assert on YAML source text from the
  server side (the calibration test loads YAML as data, which is fine; that's not
  a source-text wiring assertion).
- Assert `encounter.opposed_roll_resolved` fires for a `trial` beat (proving the
  opposed_check conversion is engaged, not narrator improv) and that
  `encounter.resolved` fires on the concede path (the lie-detector for the
  anti-soft-lock claim).

## Scope Boundaries

**In scope (this story only):**
- Edit `trial` in `sidequest-content/genre_packs/tea_and_murder/rules.yaml`:
  add a `push` + `resolution: true` withdraw/concede beat; set
  `resolution_mode: opposed_check`; lower both thresholds `8 → 7`; add
  `opponent_default_stats` (≤ 10) covering `Cunning`, `Passion`, and the new
  exit beat's `stat_check` stat.
- Tests that prove: trial always has a resolvable exit; concede resolves cleanly
  on any tier (incl. a failed roll); opposed_check engages; ADR-093 calibration
  guardrail stays green; the resolution OTEL span fires.
- Keep `tests/genre/test_confrontation_calibration.py` green (it now exercises
  `trial`); fix the stale tea_and_murder docstring if it misleads.

**Out of scope (other stories — do NOT touch):**
- `negotiation` and `scandal` opposed_check conversion → **73-1**. (`negotiation`
  already has its `walk_away` resolution beat; leave it. `scandal`'s asymmetric
  `containment`/`exposure` dials need a deliberate calibration decision that is
  73-1's, not this story's.)
- The `advance_confrontation` lost-update fix → **73-3**. Do not refactor the
  write tool here.
- Push/angle CritSuccess legibility (the "0 reads as broken roll" readout) →
  **73-4**. Do not change `DEFAULT_DELTAS` or the beat-kind reporting.
- Suppressing the re-fired `encounter.confrontation_initiated` span → **73-5**.
- No changes to `opposed_check.py` band constants, the ADR-116 `_ADVERSARIAL_CATEGORIES`
  staging, or the `social_duel`/`auction` recipes.

## AC Context

No explicit ACs existed in the backlog; these are derived from the epic's
`trial` slice and the 59-8 reference fix. Targets are testable.

**AC1 — Trial has an always-resolves withdraw/concede beat (no soft-lock).**
`trial` gains a `push` beat carrying `resolution: true`. Fixture-driving that
beat through `apply_beat` sets `enc.resolved is True` and
`outcome == "resolution_beat:<beat_id>"` on **every** outcome tier — including
Fail and CritFail. This is the anti-soft-lock guarantee.

**AC2 — Trial is converted to opposed_check.** `trial.resolution_mode ==
opposed_check`; both thresholds are `7`; an `opponent_default_stats` block
(all values ≤ 10) covers every `stat_check` stat the beats use (`Cunning`,
`Passion`, plus the exit beat's stat). Driving a non-exit beat emits
`encounter.opposed_roll_resolved` (proving both sides roll), and the opponent
conviction dial can advance off 0.

**AC3 — The concede path ends the confrontation cleanly (ADR-116
end-on-no-Other compatible).** After the concede beat resolves, the encounter is
in `EncounterPhase.Resolution` with `resolved=True` and a coherent `outcome`; no
dangling active encounter remains on the snapshot. The clean exit is compatible
with the already-wired `_resolve_if_no_opponent_remains` path.

**AC4 — ADR-093 calibration guardrail stays green with `trial` swept in.**
`tests/genre/test_confrontation_calibration.py` passes with `trial` now matching
the opposed_check filter: thresholds == 7, no `opponent_default_stats` value ==
12 or > 10.

**AC5 — The resolution OTEL span fires.** Driving the trial to resolution (via
concede, or via a dial reaching 7) emits `encounter.resolved`
(`encounter_resolved_span`). The GM panel can confirm the trial actually ended
through the engine rather than narrator hand-waving.

### Edge cases the tests must cover

- **Concede at turn 1.** A withdraw/concede on the very first beat, before either
  dial has moved, must still resolve (`resolved=True`). No "must build dial
  first" precondition.
- **Concede when the opponent is already near threshold.** Concede must resolve
  as a *voluntary exit* (`outcome == "resolution_beat:<beat_id>"`), not silently
  flip to an opponent_victory because the opponent dial happens to be at 6. The
  `resolution`-flag branch is checked after the dial-threshold branches
  (`beat_kinds.py:840–864`), so verify the ordering produces the intended
  voluntary-exit outcome when the opponent dial is high but **not yet at**
  threshold; if the opponent dial is *already ≥ threshold* on this beat the
  dial-victory branch wins first — that's by design, document the expectation in
  the test.
- **Soft-lock regression — a trial with no resolvable beat must now be
  impossible.** Assert structurally (over the loaded `trial` `ConfrontationDef`)
  that at least one beat carries `resolution: true` (or a `push` whose
  `DEFAULT_DELTAS` resolution semantics always terminate). This is the regression
  tripwire for the soft-lock; it interrogates loaded model data, not source text.
- **Failed concede roll still resolves.** Explicitly drive the concede beat at a
  `Fail`/`CritFail` tier and assert `resolved=True` — the exact bug 59-8 found
  (a `push` without the flag only resolves on Success, trapping the player).

## Assumptions

1. **The `trial` opponent is location/role-seated, not roster-stat-blocked**
   (the tribunal/prosecution is a scene fixture, like `social_duel`'s Sir Iain),
   so `opponent_default_stats` is the live stat source and must carry every
   `stat_check` stat the beats use — otherwise `resolve_opponent_modifier` fails
   loud. If a future world seats a stat-blocked NPC prosecutor, its per-actor
   stats take precedence; the default block remains the fallback.
2. **The stale calibration-test docstring** (tea_and_murder "social-only / no
   opposed_check") predates 59-8's `social_duel` conversion and is already
   inaccurate; this story makes it more so. Correcting it is in scope as a
   docstring fix, not a behavioral change.
3. **ADR-116 `social` empty-opponent enforcement stays deferred.** This story
   relies on opposed_check opponent-*seating* (existing) but does NOT advance the
   ADR-116 §3 staging to enforce `NoOpponentAvailableError` for `social`. If a
   trial somehow instantiates with no Other, the existing social-exempt behavior
   (narration fallback) stands; closing that gap is separate, deliberate work.
4. **Choice of exit-beat label/stat is an authoring decision.** "Withdraw the
   Charge", "Concede the Point", "Step Down", or similar — any drawing-room-true
   label fits. The mechanical requirements (`kind: push`, `resolution: true`,
   `base: 0`, a declared `stat_check` present in `opponent_default_stats`, a
   `consequence:` line) are fixed; the prose is the author's call.
5. **No new schema fields.** Everything needed (`resolution_mode`,
   `opponent_default_stats`, `BeatDef.resolution`, `push` kind) already exists in
   `sidequest/genre/models/rules.py`. This is a content edit plus tests, not an
   engine feature.
