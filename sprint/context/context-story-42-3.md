---
parent: context-epic-42.md
workflow: tdd
---

# Story 42-3: TensionTracker + PacingHint narrator wiring

## Business Context

`TensionTracker` produces `PacingHint` — a narrator-prompt section that tells the narrator *how* to pace the next turn (delivery mode, drama threshold, tension curve). Without it, the narrator has no scene-shape signal across a combat arc, and every round tends to read the same. `PacingHint` is the narrator's rhythm stick; losing it is the difference between a three-round combat that feels like a climax and one that reads as three identical rounds.

Target audience impact: James (narrative-first roleplayer) is the player most sensitive to pacing drift. The dual-track tension model (action + stakes) was specifically designed to keep his scenes from flattening. Ship this and combat reads like film; skip it and combat reads like a dice roller.

## Technical Guardrails

**Port scope:**
- `sidequest-api/crates/sidequest-game/src/tension_tracker.rs` (803 LOC)

**Target files (new):**
- `sidequest/game/tension_tracker.py` — `RoundResult`, `DamageEvent`, `PacingHint`, `DeliveryMode`, `CombatEvent`, `DetailedCombatEvent`, `TurnClassification`, `TensionTracker`, `classify_round(...)`, `classify_combat_outcome(...)`
- `tests/fixtures/tension/` — JSON fixtures exported from Rust via `cargo run --example tension_fixture_export`

**Target files (modified):**
- `sidequest/agents/orchestrator.py` — add `TurnContext.pacing_hint: str | None`; register Early-zone `pacing_hint` section (match Rust zone placement — confirm during port; if Rust places it in Valley, follow Rust)

**Dependencies:**
- `sidequest/genre/models/drama_thresholds.py` (existing — confirm during story setup) — `DramaThresholds` is re-exported from `sidequest_genre` in Rust; the Python port must read from the already-ported genre model, NOT re-declare Python-side constants.

**Translation key:**
- `#[non_exhaustive] enum CombatEvent` → `StrEnum`
- `TensionTracker` `&mut self` methods → Python instance methods that mutate `self`
- Rust `Option<&str> killed` → `killed: str | None`

**Patterns to follow:**
- **Fixture parity is load-bearing.** Classification tables are large (12+ `CombatEvent` variants × 5+ tension states). Generate fixtures from Rust; do not hand-transcribe. Committed fixture JSON is the parity contract.
- **Narrator prompt zone parity with Rust.** Read Rust's `inject_pacing_hint` or equivalent to confirm which `AttentionZone` the hint lands in (Early vs Valley). Zone drift changes the narrator's attention weighting — not cosmetic.

**What NOT to touch:**
- Genre pack `drama_thresholds.yaml` — pulled from `sidequest_genre` already
- Any narrator prose — this is prompt wiring, not narrator behaviour change
- `StructuredEncounter` — 42-1 scope (done before this story starts)
- Combat dispatch — 42-4 scope; `TensionTracker` lives on orchestrator/snapshot state, not on dispatch context directly

## Scope Boundaries

**In scope:**
- All types and enums: `RoundResult`, `DamageEvent`, `PacingHint`, `DeliveryMode`, `CombatEvent`, `DetailedCombatEvent`, `TurnClassification`
- `TensionTracker` state machine + all methods
- `classify_round(round_result, killed)` free function
- `classify_combat_outcome(...)` free function
- Full Rust test suite ported 1:1
- Rust fixture export script (`cargo run --example tension_fixture_export`) authored alongside, fixtures committed to `tests/fixtures/tension/`
- Orchestrator wiring: `TurnContext.pacing_hint` field + section registration
- Wiring test: orchestrator skips the `pacing_hint` section when the field is `None`; registers it when non-`None`

**Out of scope:**
- Where `TensionTracker` instances are owned (session? encounter? connection?) — that's dispatch scope (42-4). For 42-3, the tracker is constructed in test scope only; production ownership lands in 42-4.
- Any music-director / mood integration — Rust has a `MusicDirector` that consumes `PacingHint`; Python music director is not ported yet. 42-3 produces the hint; consumers land later.
- Pacing hint persistence — snapshot integration is 42-4 scope

## AC Context

**AC1: Classification parity.**
`classify_round(...)` and `classify_combat_outcome(...)` produce Rust-identical enum values on every input from the committed fixture suite. Test iterates the fixture JSON and asserts return values.
*Edge case:* `killed = None` (nobody died this round) — distinct behaviour from `killed = ""` (empty string). Preserve.

**AC2: `TensionTracker.tick(round_result)` produces Rust-parity `PacingHint`.**
Multi-round scenarios: apply a sequence of `RoundResult` values to a tracker; assert the emitted `PacingHint` per tick matches the Rust tracker's sequence byte-for-byte. Minimum 3 scenarios: escalating combat, stalling combat, reversal combat.

**AC3: `PacingHint` narrator-zone parity.**
The Python orchestrator registers `pacing_hint` in the same attention zone (Early or Valley) as the Rust orchestrator. Confirm by reading Rust source during story setup; document the choice in the port.
*Edge case:* `TurnContext.pacing_hint is None` → no section registered, zero byte leak into prompt.

**AC4: `DramaThresholds` sourced from genre pack.**
Python `TensionTracker` reads threshold values from the genre pack's drama config, not from Python-side constants. Test: a pack with overridden thresholds produces a `PacingHint` whose delivery mode shifts in the expected direction (e.g., a pack with a lower `high_drama_threshold` triggers `DeliveryMode.Urgent` at a lower tension value).

**AC5: Every Rust test ports 1:1.**
`grep '#\[test\]' sidequest-api/crates/sidequest-game/src/tension_tracker.rs` → count N. Python test file has N `def test_*` with the same names.

**AC6: Fixture regeneration is scriptable.**
Committed `cargo run --example tension_fixture_export` writes canonical JSON fixtures to `sidequest-server/tests/fixtures/tension/`. A reviewer can re-run the example to refresh fixtures if the Rust side changes. Document the command in the fixture directory's README.

## Assumptions

- **`DramaThresholds` is already ported in `sidequest_genre`.** Confirm during story setup with `grep -rn 'DramaThresholds' sidequest-server/sidequest/genre/`. If missing, porting it is in-scope for 42-3 (genre model extension, small).
- **Rust has or easily gains a fixture-export example binary.** If not, authoring one is ~20 LOC of Rust; acceptable addition to this story.
- **Narrator prompt Early/Valley zone semantics are stable.** Story 41-5 (narrator agent port) established the zones. No zone drift expected between 41-5 merge and 42-3 start.
- **`CombatEvent` enum variants are string-stable across Rust and Python.** Serde serialises enums as strings by default; if Rust uses a custom tag/content shape, match it in Python.
