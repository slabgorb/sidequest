---
id: 93
title: "Confrontation Difficulty Calibration v1"
status: accepted
date: 2026-05-04
deciders: ["Keith Avery", "The Man in Black (Architect)"]
supersedes: []
superseded-by: null
related: [33, 74, 78]
tags: [genre-mechanics]
implementation-status: live
implementation-pointer: null
---

# ADR-093: Confrontation Difficulty Calibration v1

## Context

Playtesting reveals confrontations feel grindy and brutal — players rarely
"succeed," dials creep, and resolution takes 20+ rolls. ADR-033 specified the
Confrontation Engine architecture but left calibration ("the numbers") to genre
packs and a placeholder fallback. The architecture is sound; the calibration is
not.

Empirical map of the current tuning surface (see investigation 2026-05-04):

### 1. Opponent ability score parity

`opponent_default_stats` is hardcoded to **12** across every shipped genre pack
(`elemental_harmony`, `mutant_wasteland`, `space_opera`, `caverns_and_claudes`).
That yields a D&D modifier of **+1**.

Player point-buy budget (27) produces an average modifier of roughly **+1** as
well. The player therefore enters every opposed_check at **net shift 0** before
the dice. The system was implicitly designed to give the player a small edge;
instead it gives parity.

### 2. Tie band width

`sidequest-server/sidequest/game/opposed_check.py:52–55` defines:

```
shift ≥ +10 → CritSuccess
shift ≥ +3  → Success
−2 ≤ shift ≤ +2 → Tie
shift ≤ −3 → Fail
shift ≤ −10 → CritFail
```

With two d20 rolls and parity modifiers, **p(Tie) ≈ 50%**. On Tie, beats deliver
half deltas (`base // 2`). Roughly half of all rolls produce muted progress on
both sides — the dial-creep complaint.

### 3. Threshold-to-base ratio

Most packs set `player_metric.threshold = 10` and beat base values of **2**.
That requires five clean Successes from the player. Combined with parity
shift and a wide tie band, expected rolls to resolution exceed **20**.

`victoria` is correctly proportioned (threshold 7, base 2–3). The other packs
copied the pattern without re-checking the math.

### 4. Silent failures

Strike/Brace on a Fail tier yields `own=0, opponent=0` — no penalty. Only
CritFail (shift ≤ −10, ~5% of rolls) produces a backfire. Failures feel like
"nothing happened" rather than "the opponent is closing in," which compounds
the grindy perception.

## Decision

Calibrate v1 by changing **three numbers across YAML and one constant pair in
`opposed_check.py`**. No new infrastructure. No new schema fields. No
narrator-side changes.

### Calibration set

| Lever | Before | After | Rationale |
|---|---|---|---|
| `opponent_default_stats` (per-pack) | all values 12 | all values **10** | Restore the +1 player edge that point-buy implies. Modifier moves from +1 to +0 on the opponent side. |
| Tie band (`opposed_check.py`) | `−2 ≤ shift ≤ +2` | `−1 ≤ shift ≤ +1` | Reduces p(Tie) from ~24% to ~14%; raises decisive-roll rate from ~76% to ~86%. |
| `threshold` for confrontations using `resolution_mode: opposed_check` | 10 | **7** | Filter is by resolution mode, not type name — this catches every confrontation that shares the calibrated tie-band geometry. Includes `combat` across all four packs that ship combat AND space_opera's `ship_combat` (mode = `opposed_check`, despite the name). Matches the proportion already validated in `victoria`. Cuts expected rolls-to-resolution by ~30%. |
| `threshold` for `negotiation` and other `beat_selection`-mode confrontations | unchanged (mostly 7–10) | unchanged | Different resolver path; v1 scope is the calibrated tie band only. |
| `threshold` for `dogfight` (sealed_letter_lookup mode) | 30 | 30 (no change) | Different schema and resolver; recalibrate in v2 if needed. |

### Expected behavior shift

Per-roll outcome distribution for a typical PC (mod +1) versus a calibrated
opponent (mod +0), tie band ±1, computed analytically by enumerating all 400
d20×d20 pairs:

| Tier | Calibrated (player +1, opp +0, ±1) | Pre-calibration parity (player +1, opp +1, ±2) |
|---|---|---|
| CritSuccess | 16.50% | 13.75% |
| Success | 31.00% | 24.50% |
| **Success-or-better** | **47.50%** | **38.25%** |
| Tie | 14.25% | 23.50% |
| **Fail-or-worse** | **38.25%** | **38.25%** |
| Fail | 27.00% | 24.50% |
| CritFail | 11.25% | 13.75% |

The qualitative claim still holds — player edge becomes real (Success+ rises
~9pp), ties drop sharply (~24% → ~14%), and the player-vs-opponent margin
goes from neutral (38/38) to a clear ~9pp player advantage (47/38). Total
decisive-roll rate (anything that isn't a tie) climbs from ~76% to ~86%.

Combined with `threshold = 7`, expected rolls-to-resolution drop from ~20–25 to
**~7–10**. Confrontations should now feel like decisive scenes rather than
attrition, which aligns with the SOUL "Cut the Dull Bits" principle.

> **Amendment 2026-05-04 (story 45-41):** This table replaces the earlier
> rough estimates (45% / 33% / 22%) which were back-of-envelope. The numbers
> above are exact analytical values from enumerating the 400 outcome pairs.
> The calibration's intent and the qualitative SOUL argument are unchanged;
> only the specific percentages have been corrected. The `ship_combat` row
> in the calibration set table was likewise amended to reflect that
> `ship_combat` uses `resolution_mode: opposed_check` (not sealed_letter)
> and therefore belongs in the calibrated set.

### What this ADR does NOT change

- **No schema additions.** No new `failure_delta` field, no per-PC heroic
  modifier, no narrator-side opposed_check overrides. Those are v2 candidates if
  v1 calibration leaves residual problems.
- **No Edge/Composure changes.** Pool sizes (PLACEHOLDER_EDGE_BASE_MAX = 10)
  remain. ADR-078 owns that surface.
- **No dice-display changes.** ADR-074 / ADR-075 unaffected.
- **No genre-pack-specific bespoke tables.** This is uniform calibration; per-
  pack feel-tuning is downstream of v1 measurement.

### Measurement

ADR-033 already specifies `encounter.opposed_roll_resolved`,
`encounter.beat_applied`, `encounter.metric_advance`, and `encounter.resolved`
spans (see `sidequest-server/sidequest/telemetry/spans/encounter.py`). After
v1 lands, GM-panel review should report:

- **rolls-to-resolution histogram** per confrontation type (target: median 7–10)
- **tier distribution** per opposed_check (target: ≤35% Tie)
- **player win rate** on combat/chase/negotiation (target: 55–65% — heroic but
  not guaranteed)

If those targets miss after one playtest cycle, v2 can introduce per-PC heroic
shift or asymmetric thresholds. Don't preempt that work now.

## Consequences

**Positive:**
- Confrontations resolve in roughly the right number of beats for the SOUL
  "decisive scene" pacing target.
- Players feel their character build pays off (the +1 player edge is real).
- Five YAML files + two constants — minimal blast radius. Reversible per pack.
- Existing OTEL surface measures the change without new instrumentation.

**Negative:**
- Genre packs that were playtested at the old numbers will feel easier. Acceptable
  — they were over-tuned, not balanced.
- Tie-band narrowing changes the existing distribution shape — sealed_letter
  flows that share the same shift bands inherit the change. Verify `dogfight`
  remains playable under the narrower band before shipping.
- Constants in `opposed_check.py` move with code; per-pack thresholds move with
  content. Two-PR change unless we colocate.

**Forward debt (deferred to v2):**
- Heroic-PC modifier (player gets +1d4 or auto-advantage for genre-marked
  beats).
- Failure-tier deltas (silent Fail problem).
- Per-pack feel-tuning once v1 measurements arrive.
- Recalibration of `dogfight` / `ship_combat` thresholds if the narrower tie
  band makes them too swingy.

## Alternatives Considered

1. **Raise beat base values (2 → 3 or 4).** Equivalent rolls-to-resolution
   improvement, but increases swing per roll and amplifies CritFail backfire.
   Rejected — adds variance, doesn't fix parity.

2. **Add a flat +2 player heroic shift.** Cleaner narrative ("PCs are heroes")
   but requires new schema and breaks symmetry between `opposed_check` sides.
   Defer to v2.

3. **Lower thresholds without touching opponent stats.** Cuts confrontation
   length but doesn't fix the "every roll is a tie" feel. Treats the symptom,
   not the cause.

4. **Per-genre bespoke calibration.** Premature — we don't yet have enough
   playtest evidence per pack to justify divergent tunings. Calibrate uniformly
   first, diverge when data demands it.

## Implementation Pointer

Dev story should:

1. Edit `sidequest-content/genre_packs/*/rules.yaml`:
   - `opponent_default_stats`: every numeric value 12 → 10
   - For every confrontation with `resolution_mode: opposed_check`, lower
     `player_metric.threshold` and `opponent_metric.threshold` from 10 → 7.
     This filter (resolution mode, not type name) covers `combat` across all
     four shipped combat packs AND space_opera's `ship_combat`. `chase`
     confrontations are already at 7 across packs and need no change.
   - Leave `negotiation` and other `beat_selection`-mode confrontations alone
   - Leave `dogfight` (sealed_letter_lookup, threshold 30) alone

2. Edit `sidequest-server/sidequest/game/opposed_check.py`:
   - Change Tie band constants from ±2 to ±1
   - Update any associated band-table tests

3. Verify `encounter.opposed_roll_resolved` span still emits; no telemetry
   schema change.

4. Add a unit test that asserts the calibrated tier distribution across 10k
   simulated rolls falls within ±5pp of the analytical expected distribution
   in the "Expected behavior shift" table above.

> **Implementation status (2026-05-04, story 45-41):** Live. All four packs
> calibrated, opposed_check band narrowed, distribution and YAML calibration
> tests passing.

5. Playtest one confrontation per genre pack and capture `rolls-to-resolution`
   from OTEL. Report against the median 7–10 target before closing.
