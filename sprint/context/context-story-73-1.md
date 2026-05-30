---
parent: context-epic-73.md
workflow: tdd
---

# Story 73-1: Convert negotiation + scandal to opposed_check

> Epic 73 (Confrontation Engine Hardening) · 5 pts · workflow **tdd** · type **bug** ·
> repos **sidequest-content**, **sidequest-server**.
> Sibling stories (out of scope here): **73-2** (trial), **73-3** (advance_confrontation
> lost-update), **73-4** (push CritSuccess legibility), **73-5** (re-fired span). Do not
> touch them.

## Business Context

This story generalizes the **Story 59-8** `social_duel` fix (Glenross / `tea_and_murder`
playtest) to two more siblings in the same drawing-room social-confrontation family:
`negotiation` (Polite Negotiation) and `scandal` (Scandal Eruption). Both still run the
default `beat_selection` resolution mode, where **only the player rolls a d20** and the
opponent's dial moves only when the narrator hand-picks a delta via the
`advance_confrontation` write tool. That is the same structural unfairness 59-8 found in
`social_duel`: a Conflict (two-sided contest) resolved by a Challenge resolver (one side
rolls). Consequences, verbatim from the epic: the opponent dial can freeze at 0 so the
confrontation can never resolve on the opponent's side, and the GM panel sees "Claude
said delta=N" instead of an honest opposed roll.

**Who this serves.** `tea_and_murder`'s social confrontations are the pack's *primary
mechanical surface* — this is the Glenross line that Keith and Jade (both forever-GMs)
run, and Sebastien + Jade are the two mechanics-first players who specifically miss
crunch that doesn't fire. Converting these to `opposed_check` means both sides roll
d20+modifier each beat, the tier derives from the ADR-093 shift bands, and the
`encounter.opposed_roll_resolved` OTEL span gives the GM panel a real, auditable
resolution. The math becomes legible in the player-facing readout — exactly the
"can Sebastien/Jade see the math?" test from the playgroup rubric. (This is a player-UI /
honest-mechanics concern, not a dev-observability one.)

`social_duel` is the **already-converted reference shape** in the same
`rules.yaml` — match it, don't reinvent it.

## Technical Guardrails

**This is primarily content (`rules.yaml`) work with a server-side guardrail-test
sweep.** No new schema fields, no new resolution infrastructure — the
`opposed_check` path and its calibration test already exist and were proven by 59-8.

### The reference recipe (copy `social_duel`)
`sidequest-content/genre_packs/tea_and_murder/rules.yaml`, the `social_duel` entry
(currently lines ~303–378), is the worked example. Its converted shape:

- `resolution_mode: opposed_check`
- an `opponent_default_stats:` block keyed by the **same stat names the beats'
  `stat_check` uses** (so `resolve_opponent_modifier` can source the opponent's
  modifier when the Other is location-seated with no per-actor sheet), **every value
  ≤ 10** (ADR-093 parity ceiling — challenge comes from dial/DC geometry, not stat
  inflation; 10 → +0 modifier).
- `player_metric.threshold == opponent_metric.threshold == 7` (ADR-093 `opposed_check`
  calibration) — **see the scandal exception below, this is the load-bearing design
  decision of the story.**
- a terminal `push` beat with `resolution: true` so the voluntary exit always resolves
  (kills the soft-lock 59-8 closed). `negotiation` *already* carries this — `walk_away`
  (`kind: push`, `resolution: true`); `scandal`'s `weather_it` (`kind: push`) **does
  not yet** and will need it.

### Server seams the conversion exercises (read, do not re-implement)
- `sidequest-server/sidequest/game/opposed_check.py` — `resolve_opposed_check`
  (both sides roll d20+mod → shift → tier), `resolve_opponent_modifier` (stat sourcing:
  `per_actor_state['stats']` → `cdef.opponent_ability_scores()` → **fail-loud
  `ValueError`** if neither carries the stat). Modifier = `floor((score-10)/2)`.
- `sidequest-server/sidequest/server/narration_apply.py:4118`
  `_resolve_opposed_check_branch` — rolls both sides, calls `resolve_opposed_check`,
  emits `encounter.opposed_roll_resolved` (via `encounter_opposed_roll_resolved_span`,
  line ~4472) **before** applying beats, then `apply_beat` once per side.
- `sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py:369`
  `_requires_opponent` — already folds `opposed_check` into opponent-seating (ADR-116),
  so a converted social confrontation seats an opponent-side Other from `npcs_present`
  or the location fallback. No change needed here; rely on it.
- `sidequest-server/sidequest/genre/models/rules.py` — `ConfrontationDef`,
  `ResolutionMode` (line 310), `opponent_default_stats` (line 460),
  `opponent_ability_scores()` (line 602, strips `OPPONENT_RESERVED_STAT_KEYS` =
  `hp`/`armor_class` so combat-seed keys never resolve as ability mods),
  `BeatDef.resolution` override (line ~151).

### The calibration guardrail test (must stay green)
`sidequest-server/tests/genre/test_confrontation_calibration.py` is the ADR-093
enforcement. `tea_and_murder` is already in its `SHIPPED_PACKS` list, so the moment
`negotiation`/`scandal` declare `resolution_mode: opposed_check` they are **swept into**:
- `test_opponent_default_stats_no_parity_12_remains` — no `opponent_default_stats` value
  may be 12 or > 10 (reserved `hp`/`armor_class` exempt).
- `test_opposed_check_thresholds_calibrated_to_7` — **both** `player_metric.threshold`
  and `opponent_metric.threshold` must equal **7** for every `opposed_check`
  confrontation.

`tea_and_murder` is deliberately excluded from `COMBAT_PACKS` (it is social-only), so the
"must expose an opposed_check confrontation" wiring guard does **not** apply — converting
these does not change that.

### Test discipline (TDD, server rule)
- **Behavioral / span assertions only — never grep production source** (server CLAUDE.md
  "No Source-Text Wiring Tests"). Assert the `opposed_check` path actually runs:
  drive a `negotiation`/`scandal` turn through `_resolve_opposed_check_branch` against a
  synthetic snapshot and assert the **`encounter.opposed_roll_resolved` span fired** and
  the opponent dial advanced.
- The calibration test is the YAML-level guardrail; add at least one
  **behavior/integration** test that the converted recipe resolves end-to-end (player
  reaches threshold, OR the terminal `push` resolution beat fires), proving the
  frozen-dial soft-lock is gone — not just that the YAML parses.
- OTEL span assertion is the wiring test per the OTEL Observability Principle.

## Scope Boundaries

**In scope (73-1):**
- `negotiation` → `opposed_check` in `tea_and_murder/rules.yaml`: add
  `opponent_default_stats` (≤10) keyed by its beats' stats (`Cunning`, `Nerve`);
  thresholds already 7/7 — keep them at 7. `walk_away` push already has
  `resolution: true` — keep it.
- `scandal` → `opposed_check`: add `opponent_default_stats` (≤10) keyed by its beats'
  stats (`Cunning`, `Pride`, `Nerve`); **deliberately recalibrate its asymmetric dials
  (see AC Context)**; ensure a terminal always-resolves push (`weather_it` needs
  `resolution: true`).
- Exercise/extend the `_resolve_opposed_check_branch` + `resolve_opposed_check` path for
  these two recipes; keep `test_confrontation_calibration.py` green; add the
  resolvability + span behavior tests.

**Out of scope (do NOT touch):**
- `trial` conversion + soft-lock fix → **73-2**.
- `advance_confrontation` lost-update → **73-3**. (Do not modify
  `advance_confrontation.py` / `tool_registry.py`.)
- push CritSuccess legibility / beat-kind readout → **73-4**.
- re-fired `encounter.confrontation_initiated` span → **73-5**.
- `social_duel` (already done in 59-8) and `auction` (`table_resolution` — different
  resolver, leave inert beats alone).
- The `opposed_check.py` shift-band constants and the `±1` tie band — those are ADR-093
  v1, already live. Do not retune them.

## AC Context

Derived ACs (no explicit ACs existed; 5–6 testable, TDD-ready):

**AC-1 — negotiation converts to opposed_check and is two-sided.**
`negotiation.resolution_mode == opposed_check`, with an `opponent_default_stats` block
(≤10) covering every stat its beats `stat_check` against (`Cunning`, `Nerve`). A driven
turn routes through `_resolve_opposed_check_branch`; **both** the player and the opponent
`leverage` dial can advance from their own d20 rolls (no longer frozen at the `starting:
3`). Thresholds stay 7/7.

**AC-2 — scandal converts to opposed_check with a DELIBERATE asymmetric-dial decision.**
`scandal.resolution_mode == opposed_check` with `opponent_default_stats` (≤10) covering
`Cunning`/`Pride`/`Nerve`. **Scandal's dials are asymmetric** today:
`player_metric` = `containment` threshold **5**, `opponent_metric` = `exposure` threshold
**8** — a deliberate fiction (the player races to contain before the gossip goes public,
and the gossip has a head start). The ADR-093 guardrail
(`test_opposed_check_thresholds_calibrated_to_7`) demands **both thresholds == 7** for any
`opposed_check` confrontation. **These are in direct tension and the resolution must be a
documented design choice, not a blind 7-stamp.** The chosen calibration for this story
(see Assumptions for rationale):
**set both `containment` and `exposure` thresholds to 7**, preserving the
*fiction's asymmetry through the dial geometry instead of the threshold* — i.e. keep
`exposure.starting` ahead of `containment.starting` (and/or rely on the opponent's
turn-by-turn advance) so exposure still has its head start, while both sides share the
calibrated tie-band threshold the guardrail and the `opposed_check` resolver require. The
asymmetry moves from *unequal finish lines* to *unequal start lines*. **Document the
decision inline in `rules.yaml`** (a comment mirroring `social_duel`'s threshold
comment), and capture *why* in the AC/test docstring. The implementer may, after reading
ADR-093 §"What this ADR does NOT change" and §"Forward debt" (asymmetric thresholds are
explicitly a v2 candidate), instead argue for a guardrail amendment — but the **default
and expected outcome is both==7 with the head-start moved to `starting`**, because v1
calibration owns the threshold and this story is not chartered to introduce asymmetric-
threshold support into the guardrail.

**AC-3 — both pass the ADR-093 calibration guardrail.**
`tests/genre/test_confrontation_calibration.py` stays green for `tea_and_murder` with
`negotiation` and `scandal` now declaring `opposed_check`: no `opponent_default_stats`
value is 12 or > 10, and every `opposed_check` threshold (now including both new
confrontations) == 7.

**AC-4 — each confrontation is actually RESOLVABLE (no frozen-dial soft-lock).**
For each of `negotiation` and `scandal`, a behavior test drives beats to a terminal
state: either a dial crosses threshold 7 from real opposed rolls, **or** the terminal
`push` beat (`negotiation.walk_away`, `scandal.weather_it`) carries `resolution: true`
and ends the confrontation on **any** outcome tier. `scandal.weather_it` must gain
`resolution: true` (it lacks it today). This proves the 59-8 soft-lock class is closed
for both siblings.

**AC-5 — the opposed-roll OTEL resolution span fires.**
Driving a converted `negotiation`/`scandal` turn through `_resolve_opposed_check_branch`
emits `encounter.opposed_roll_resolved` (`encounter_opposed_roll_resolved_span`) **before**
beats apply, carrying both sides' roll+mod+shift+tier. Assert the span fired (the
behavioral wiring test) — the GM-panel lie-detector now shows a real opposed roll for
these confrontations instead of a narrator-fiat delta.

**AC-6 (edge) — opponent stat sourcing fails loud, and the no-Other case is handled.**
- *Stat sourcing:* every stat a converted beat checks must be present in
  `opponent_default_stats` (or on the seated actor's `per_actor_state['stats']`). If a
  beat's `stat_check` names a stat absent from both, `resolve_opponent_modifier` raises a
  loud `ValueError` (No Silent Fallbacks) — a test should assert a *complete*
  `opponent_default_stats` so this never trips at the table, and (optionally) assert the
  fail-loud on a deliberately-incomplete fixture.
- *No Other (ADR-116):* `_requires_opponent` already returns `True` for `opposed_check`,
  so the lifecycle seats an opponent-side Other (from `npcs_present` or the location
  fallback). The converted recipes must not regress that — a confrontation that somehow
  reaches resolution with no Other seated is an ADR-116 invariant violation; the
  conversion relies on the existing seating, and the resolvability test implicitly
  confirms an Other is present (its dial moves).

## Assumptions

- **Scandal's asymmetric-dial decision (the central judgment call).** The default,
  expected resolution is **both thresholds → 7**, with scandal's intended head-start
  preserved by moving the asymmetry into the **starting values** (e.g. `exposure`
  starts ahead of `containment`) and/or the opponent's per-turn advance, **not** the
  finish line. Rationale: (1) ADR-093 explicitly scopes asymmetric thresholds to **v2**
  ("Forward debt: ... asymmetric thresholds") and states v1 calibration "owns the
  threshold"; (2) the `opposed_check` resolver and `test_opposed_check_thresholds_-
  calibrated_to_7` both assume symmetric 7/7 — honoring them keeps blast radius minimal
  and avoids smuggling unscoped v2 work into a 5-point bug story; (3) the gothic fiction
  ("gossip has a head start, player races to contain") survives intact as a *start-line*
  asymmetry. **The decision must be written into `rules.yaml` as an inline comment**
  (mirroring `social_duel`'s threshold note) so a future author sees the reasoning. If
  the implementer believes the fiction genuinely requires unequal *finish lines*, that is
  a guardrail/ADR-093 amendment and should be escalated — it is **not** silently encoded
  by relaxing the test.
- `negotiation` already has thresholds 7/7 and a `resolution: true` `walk_away` push, so
  its conversion is largely adding `opponent_default_stats` + flipping
  `resolution_mode`. Verify `opponent_metric.starting: 3` still reads sensibly under
  opposed_check (it gave the opponent a head start under beat_selection; confirm it's
  intentional, not a frozen-dial artifact — likely keep as a start-line edge).
- Stat coverage: `negotiation` beats check `Cunning`/`Nerve`; `scandal` beats check
  `Cunning`/`Pride`/`Nerve`. `opponent_default_stats` must key **exactly** these
  (case matters only for the loud-fail message path; the resolver does a
  case-insensitive walk, but match the `ability_score_names` casing —
  `Cunning`/`Nerve`/`Pride` — for legibility).
- Use 10 for opponent stats (the `social_duel` precedent → +0 modifier, "competent but
  fair"), unless the fiction wants a specific NPC edge; never exceed 10.
- The `auction` (`table_resolution`) recipe is untouched — its inert beats are not part
  of the dial/opposed_check path.
- Tests run via `just server-test` / `uv run pytest`; calibration test lives under
  `tests/genre/`. Content changes are validated by that test loading the live
  `rules.yaml` (it reads `sidequest-content/genre_packs/<pack>/rules.yaml` off disk,
  parents[3] from the test file), so the YAML edit and the server test are coupled in one
  green run.
