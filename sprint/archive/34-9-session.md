---
story_id: "34-9"
jira_key: null
epic: "34"
workflow: "tdd"
---
# Story 34-9: Narrator outcome injection — RollOutcome shapes narration tone

## Story Details
- **ID:** 34-9
- **Jira Key:** not required (internal story tracking)
- **Branch:** feat/34-9-narrator-outcome-injection
- **Epic:** 34 (3D Dice Rolling System — MVP)
- **Workflow:** tdd
- **Points:** 3
- **Priority:** p1
- **Repos:** sidequest-api
- **Stack Parent:** 34-4 (Dispatch integration — beat selection emits DiceRequest, awaits DiceThrow)

## Context

### Preceding Work Complete

**34-3 and 34-4 are shipping today (2026-04-12):**
- **34-3** (3 pts): `resolve_dice()` pure function generates `RollOutcome` (CritSuccess / Success / Fail / CritFail)
- **34-4** (5 pts): Dispatch layer intercepts beat selection, generates seed, broadcasts `DiceRequest` to all clients, awaits `DiceThrow`, calls `resolve_dice()`, broadcasts `DiceResult`

The `DiceResult` payload already includes `RollOutcome` and lands in the dispatch pipeline before narration begins. The outcome exists; it's not being used.

### What This Story Does

**34-9 injects `RollOutcome` into the narrator prompt context.** The narrator (Claude) receives the roll result tone tag and shapes the prose accordingly:

- **CritSuccess** → Enthusiastic, triumphant narration. "The blow lands perfectly!"
- **Success** → Confident, positive narration. "You succeed."
- **Fail** → Dramatic setback. "The attempt falters."
- **CritFail** → Catastrophic narration. "Everything goes horribly wrong!"

The mechanism is the **prompt context zone** in `sidequest-agents`. When the dispatcher triggers narration after dice resolution, it passes the `RollOutcome` as a visible tag to Claude. Claude's system prompt already interprets outcome tags; this story just ensures the tag arrives.

### Key Architecture

1. **Data flow:**
   - `dispatch/beat.rs` calls `resolve_dice()` → gets `ResolvedRoll` with `outcome: RollOutcome`
   - `DiceResult` payload is composed with the outcome
   - `DiceResult` is broadcast to clients
   - Dispatch layer routes to narration with outcome context
   - Narrator prompt construction includes the outcome tag

2. **Prompt injection point:**
   - File: `sidequest-agents/src/narrator_prompt.rs` (or similar)
   - Existing prompt structure already has a context zone for mechanical facts (damage taken, attribute changes)
   - Add `RollOutcome` as a visible tag: `[DICE_OUTCOME: CritSuccess]` or similar
   - Claude's system prompt already knows how to interpret these tags

3. **Integration boundary:**
   - Dispatch layer has `ResolvedRoll` with outcome
   - Narrator context builder receives outcome as a parameter
   - No protocol changes (outcome already on the wire)
   - No game logic changes (outcome already generated)
   - Pure wiring: make the outcome visible to the narrator

### Testing Strategy

1. **Unit tests** — Narrator context builder:
   - Test that each `RollOutcome` variant produces the correct prompt tag
   - Test that outcome is present in the final prompt string
   - Verify other context (damage, attributes) is not affected

2. **Integration test** — Full dispatch → narration flow:
   - Mock `dispatch_beat_selection` with a known outcome
   - Verify the narrator context includes the outcome tag
   - Confirm the narration reflects the tone (this requires a mock Claude response or assertion on the prompt sent to Claude)

3. **Wiring test** — End-to-end:
   - Prove that `ResolvedRoll.outcome` flows through dispatcher → narrator context builder → prompt construction
   - Verify the complete prompt artifact contains the outcome tag

### OTEL Observations

**34-11 owns the telemetry**, but this story should document what is observable:
- Dispatcher receives `DiceResult` with outcome (34-4 already emits `dice.result_broadcast` span)
- Narrator context builder receives outcome parameter
- Add an OTEL event to narrator context construction: `narrator.outcome_injected` with outcome variant

Do NOT add OTEL to this story's scope — that lives in 34-11. Just ensure the outcome is observable via existing 34-4 telemetry and through prompt inspection.

### Acceptance Criteria

1. **Outcome is visible in narrator prompt context**
   - Every RollOutcome variant (CritSuccess / Success / Fail / CritFail) produces a distinct, identifiable tag in the prompt
   - Tag format is unambiguous (Claude must parse it reliably)
   - Tag placement is in the mechanical context zone, not in narrative prose

2. **Narrator responds to outcome tone**
   - Playtested with a single session: roll CritSuccess, roll Fail, verify narration tone matches
   - No roll-outcome changes to game state (outcome is for prose only)
   - Outcome does not override other mechanical facts (damage still applies regardless of outcome)

3. **No dispatch wiring changes**
   - 34-4's dispatch flow is unchanged
   - Outcome injection is a context-builder concern, not a dispatcher concern
   - If 34-4 needs to change to wire outcome to the narrator, this is a blocker — escalate

4. **Prompt is stable**
   - Same roll outcome + same beat should produce the same prompt (modulo state changes)
   - Narrator's system prompt does not change
   - Only the context zone is extended

5. **Tests green**
   - All narrator context tests pass
   - All integration tests pass
   - No wiring test needed (outcome is already on the wire from 34-4)

### Reference

- **Epic context:** `sprint/context/context-epic-34.md`
- **Design docs:** ADRs 074, 075; `sprint/planning/prd-dice-rolling.md`
- **34-4 dispatch logic:** `sidequest-api/crates/sidequest-server/src/dispatch/beat.rs`
- **Narrator agent:** `sidequest-api/crates/sidequest-agents/src/`
- **Protocol:** `sidequest-protocol/src/message.rs` — `RollOutcome` enum + wire payload

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-12T22:10:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-12T22:10:00Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

No upstream findings.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

No deviations yet.
