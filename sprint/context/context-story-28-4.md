---
parent: context-epic-28.md
---

# Story 28-4: Wire format_encounter_context() into Narrator Prompt

## Business Context

`format_encounter_context()` on StructuredEncounter produces a complete narrator prompt
block with phase, metric, available beats, secondary stats, and cinematography hints.
It has zero non-test callers. Instead, `dispatch/prompt.rs:335-374` builds encounter
context inline with ad-hoc formatting that doesn't include beats, stat_checks, or
cinematography. The narrator never knows what mechanical actions are available.

## Technical Approach

### What to replace

`dispatch/prompt.rs:335-374` — the block guarded by `// Structured encounter context`:
```rust
let encounter = if ctx.combat_state.in_combat() {
    Some(sidequest_game::StructuredEncounter::from_combat_state(ctx.combat_state))
} else {
    ctx.chase_state.as_ref().map(sidequest_game::StructuredEncounter::from_chase_state)
};
// ... inline formatting with push_str
```

### What to replace it with

```rust
if let Some(ref enc) = ctx.encounter {
    if let Some(def) = ctx.find_confrontation_def(&enc.encounter_type) {
        state_summary.push_str(&enc.format_encounter_context(def));
    }
}
```

Note: this still uses `ctx.encounter` which is `Option<StructuredEncounter>` already
on GameSnapshot (story 16-2 added it). Until 28-7 promotes it to the sole model, this
can temporarily coexist — but the inline combat/chase context MUST be replaced, not
duplicated alongside.

### What format_encounter_context produces

See `encounter.rs:557-653`. Output example for a standoff:
```
[STANDOFF]
Phase: ESCALATION | Beat: 3 | Tension: 7/10
Focus: 8/10 — spendable
Nerve: 6/10 — spendable
Available:
  1. Size Up [CUNNING] (tension +2), reveals opponent_detail
  2. Bluff [NERVE] (tension +3), risk: opponent may call it
  3. Draw [DRAW], resolves encounter
Camera: Close-up, slow-motion | Pace: Peak intensity | Sentences: 2-4
```

This is far richer than the current inline formatting.

## Key Files

| File | Action |
|------|--------|
| `sidequest-server/src/dispatch/prompt.rs` | Replace lines 335-374 with format_encounter_context() call |

## Acceptance Criteria

| AC | Detail | Wiring Verification |
|----|--------|---------------------|
| Replaces inline | The old inline encounter formatting (from_combat_state/from_chase_state + push_str) is removed | `grep "from_combat_state" dispatch/prompt.rs` returns nothing |
| Calls format_encounter_context | `format_encounter_context()` is called from dispatch/prompt.rs | `grep "format_encounter_context" dispatch/prompt.rs` returns a result |
| Includes beats | Narrator prompt includes available beat options with stat_checks | Test: verify prompt string contains "Available:" and beat labels |
| Includes cinematography | Narrator prompt includes camera/pacing hints | Test: verify prompt contains "Camera:" |
| OTEL | encounter.context_injected event with encounter_type, phase, beat_count | Grep: WatcherEventBuilder "context_injected" in prompt.rs |
| Wiring | format_encounter_context has a non-test consumer | `grep -r "format_encounter_context" crates/sidequest-server/ --include="*.rs" | grep -v test` returns results |

## Scope Boundaries

**In scope:** Replacing inline prompt context with format_encounter_context()
**Out of scope:** Changing the narrator agent's rules sections (28-6), applying beats (28-5)
