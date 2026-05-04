# Story 45-42: Confrontation Difficulty Calibration v1

> **Note:** Originally tracked as 45-41 during setup/red/green/review phases. Renumbered to 45-42 at finish-time after tracker collision with the OTEL-exporter-flow-fix story (origin's 45-41, merged earlier 2026-05-04). Subrepo branches and PRs (`feat/45-41-confrontation-calibration-v1`, sidequest-server#190, sidequest-content#177) keep the original 45-41 label — the YAML id is the canonical tracker.

## Overview

This story implements the calibration prescribed by ADR-093 (Confrontation Difficulty Calibration v1). Playtests reveal confrontations feel grindy with ~20–25 rolls to resolution due to three numeric factors:

1. **Opponent stats parity** — hardcoded `opponent_default_stats: 12` yields a modifier of +1, matching the player's point-buy average. The system was designed to give players an edge; it currently doesn't.
2. **Wide tie band** — `−2 ≤ shift ≤ +2` produces ~50% ties on any roll, muting progress and creating dial-creep.
3. **High thresholds** — confrontation thresholds set to 10, requiring five clean player victories to resolve.

ADR-093 prescribes three numeric levers to fix this: opponent stats 12→10, tie band ±2→±1, and thresholds 10→7 (combat/chase only). Expected outcome: median 7–10 rolls to resolution, 45% Success/CritSuccess, 33% Tie, 22% Fail/CritFail.

## Implementation Pointer

ADR-093 "Implementation Pointer" section (lines 169–192) lists exact files and changes:

### Files to Edit

**sidequest-content** (5 files):
- `genre_packs/caverns_and_claudes/rules.yaml` — opponent_default_stats: change all 12→10; combat/chase thresholds 10→7
- `genre_packs/elemental_harmony/rules.yaml` — same pattern
- `genre_packs/mutant_wasteland/rules.yaml` — same pattern
- `genre_packs/space_opera/rules.yaml` — same pattern
- `genre_packs/victoria/rules.yaml` — same pattern (victoria negotiation already at 7; dogfight/ship_combat at 30 unchanged)

**sidequest-server** (2 constants):
- `sidequest/game/opposed_check.py` lines ~52–55 — change tie band from `−2 ≤ shift ≤ +2` to `−1 ≤ shift ≤ +1`
- Update band-table tests if they hardcode shift values

**sidequest-server** (1 new test):
- `tests/server/test_*_monte_carlo_distribution.py` (new file or added to existing test module) — 10,000 simulated rolls at calibrated parameters, assert distribution within ±5% of ADR-093 expected

## Acceptance Criteria

1. Every genre pack `rules.yaml` has `opponent_default_stats` values changed from 12 to 10. Verify via `grep` that no value 12 remains in opponent_default_stats blocks across all five packs.
2. Tie band constants narrowed from ±2 to ±1 in `opposed_check.py`. Shift thresholds: ≥+2 → Success, −1 ≤ shift ≤ +1 → Tie, ≤−2 → Fail; CritSuccess/CritFail unchanged (±10).
3. Combat and chase confrontations across all genre packs have `player_metric.threshold` and `opponent_metric.threshold` lowered from 10 to 7. Negotiation remains at 7; dogfight/ship_combat at 30.
4. Monte-Carlo distribution test (10k rolls, player +1 vs opponent +0, tie band ±1) asserts tier distribution within ±5pp of: 45% Success-or-better, 33% Tie, 22% Fail-or-worse.
5. Existing opposed_check unit tests pass; any test that hardcoded shift = ±2 → Tie updated with change documented in deviation log.
6. `just check-all` passes.
7. OTEL span surface unchanged — same attribute schema on encounter.opposed_roll_resolved, encounter.beat_applied, encounter.metric_advance, encounter.resolved.

## Context & Rationale

**Current state (pre-v1):**
- p(Tie) ≈ 50% on a typical roll (two d20s, parity modifiers, ±2 band)
- Expected rolls to resolution: 20–25 (combines high tie rate + threshold=10)
- Player doesn't feel character build matters (edge is illusory)
- Confrontations feel like attrition, not decisive scenes

**Calibrated state (post-v1):**
- p(Tie) drops to ~33% (narrower band, better flow)
- Expected rolls to resolution: 7–10 (meets SOUL "decisive scene" pacing)
- Player edge is real (mod +1 vs opponent +0)
- Outcomes are more evenly distributed; no outcome dominates the roll table

**Math reference:** See ADR-093 lines 85–97 for the full expected distribution table and derivation. This story implements, not designs; math is in the ADR.

## Verification

- OTEL span surface unchanged — no new telemetry schema fields.
- Existing `encounter.opposed_roll_resolved` span continues to capture roll outcomes; GM panel can measure rolls-to-resolution and tier distribution via existing events.
- Pre-implementation: run one playtest confrontation per genre pack, measure rolls-to-resolution, report against median 7–10 target.

## Related ADRs & Stories

- **ADR-093** — Full specification, math, alternatives considered, measurement strategy
- **ADR-033** — Confrontation Engine architecture (unaffected; this is tuning, not architecture)
- **ADR-074** / **ADR-075** — Dice display (unaffected)
- **ADR-078** — Edge/Composure (unaffected; no pool-size changes)

## Notes

- This is **v1 calibration only**. Forward debt (deferred to v2): heroic-PC modifier, failure-tier deltas (silent Fail problem), per-pack feel-tuning once v1 measurements arrive, and dogfight/ship_combat recalibration if the narrower tie band causes swing issues.
- No new infrastructure, no schema additions. Pure numeric tuning.
- Changeset is reversible per-pack if playtesting reveals over-correction.
