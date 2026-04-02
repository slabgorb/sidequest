# Story 15-17: Wire Chase Cinematography

## Problem Statement

Chase cinematography has a complete, tested pipeline in `chase_depth.rs` but is never called from the dispatch layer. The `ChaseState::format_context()` method exists but has zero non-test callers, so narrator prompts never receive chase depth information (phase, danger level, camera angles, prose length guidance).

## Cinematography Pipeline (Complete)

The chase_depth.rs module contains these functions, all exported and tested:

1. **phase_for_beat()** — determine ChasePhase (Setup, Opening, Rising, Climax, Resolution)
2. **danger_for_beat()** — calculate danger escalation across beats
3. **terrain_modifiers()** — compute danger/damage penalties from terrain
4. **apply_terrain_to_rig()** — reduce rig speed/maneuver based on terrain
5. **camera_for_phase()** — select camera angle (Wide, Medium, Close, Tactical)
6. **cinematography_for_phase()** — prose style directives per phase
7. **sentence_range_for_drama()** — suggested sentence count based on danger
8. **format_chase_context()** — format all above into narrator prompt text

Lines ~481-544 in chase_depth.rs.

## Where It Should Be Wired

dispatch/prompt.rs in `build_prompt_context()`:

- Around line 449, chase_state is already checked: `} else if ctx.chase_state.is_some() {`
- This is where chase geography lore categories are prioritized
- **Missing:** After this priority logic, should also call `chase_state.format_context()` and inject into state_summary

Pattern matches existing context injection (tone, lore, trope):

```rust
// Inject tone context (line ~412)
if let Some(ref ac) = ctx.axes_config {
    let tone_text = sidequest_game::format_tone_context(ac, ctx.axis_values);
    if !tone_text.is_empty() {
        state_summary.push_str(&tone_text);
    }
}
```

Similar pattern should apply to chase_state.

## Implementation Details

### Function Signature

`ChaseState::format_context(&self, decisions: Vec<sidequest_game::chase_depth::BeatDecision>) -> String`

The function takes a `decisions` Vec. According to chase.rs line ~260, `current_beat()` method computes the beat from these decisions. For the narrator prompt context, we likely want empty decisions (the cinematography is descriptive, not prescriptive).

### Where in build_prompt_context()

After the lore context section ends (around line 535), before or alongside other subsystem context. Good locations:

1. **After lore context** (line ~535) — organized by system (tone → lore → chase cinematography)
2. **Near the combat check** (line ~447) — both combat and chase are dramatic, high-intensity modes

Prefer location 1 for clarity.

### OTEL Event Required

Per CLAUDE.md OTEL principle: every backend fix must emit telemetry so GM panel can verify.

Event: `chase.context_injected`
Fields:
- `phase` — current ChasePhase (Setup, Opening, Rising, Climax, Resolution)
- `danger_level` — danger value derived from terrain
- `camera` — camera mode (Wide, Medium, Close, Tactical)
- `sentence_range` — tuple of min/max sentence suggestions

Code pattern (reference: line ~499-504 lore.semantic_retrieval event):

```rust
WatcherEventBuilder::new("chase", WatcherEventType::StateTransition)
    .field("event", "chase.context_injected")
    .field("phase", format!("{:?}", beat.phase))
    .field("danger_level", beat.terrain_danger)
    .field("camera", format!("{:?}", camera_for_phase(beat.phase)))
    .field("sentence_range", format!("{}–{}", min_sentences, max_sentences))
    .send(ctx.state);
```

## Related Code Sections

- `/sidequest-api/crates/sidequest-game/src/chase_depth.rs` — full pipeline (481+ LOC)
- `/sidequest-api/crates/sidequest-game/src/chase.rs` — ChaseState struct and format_context() method (line 274)
- `/sidequest-api/crates/sidequest-server/src/dispatch/prompt.rs` — build_prompt_context() function (~700 LOC)
- `/sidequest-api/crates/sidequest-server/src/dispatch/mod.rs` — DispatchContext struct (line ~46, chase_state field at line ~61)

## Tests Already Passing

chase_depth.rs has integration tests (lines ~805-864):
- `format_chase_context_produces_all_sections()` — validates all sections output
- `format_chase_context_fuel_warning()` — validates warning on low fuel

These validate the formatting pipeline in isolation. After wiring, we need a wiring test in dispatch/prompt.rs that verifies format_context() is called and its output is in the final state_summary.

## Notes

- Personal project, no Jira
- Zero silent fallbacks — if chase_state is present, format_context() MUST be called
- If format_context() is called, its output MUST appear in state_summary
- OTEL event MUST fire when chase context is injected
