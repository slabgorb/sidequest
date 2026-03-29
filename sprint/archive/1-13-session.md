---
story_id: "1-13"
jira_key: "none"
epic: "1"
workflow: "trivial"
---
# Story 1-13: Extract CreatureCore — shared struct for Character and NPC fields

## Story Details
- **ID:** 1-13
- **Epic:** 1 (Rust Workspace Scaffolding)
- **Jira Key:** none (personal project, no Jira integration)
- **Workflow:** trivial
- **Type:** refactor
- **Points:** 2
- **Priority:** p0
- **Stack Parent:** 1-6 (done)

## Story Summary

Extract the 9 shared fields and 2 shared behaviors from `Character` and `NPC` into a `CreatureCore` embedded struct. Both types will compose `CreatureCore` instead of duplicating these fields.

### Shared Fields to Extract
- `name`
- `description`
- `personality`
- `level`
- `hp`
- `max_hp`
- `ac`
- `inventory`
- `statuses`

### Shared Behavior to Extract
- `apply_hp_delta()` method
- `Combatant` trait implementation

## Workflow Tracking
**Workflow:** trivial
**Phase:** setup
**Phase Started:** 2026-03-25

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-25 | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

No design deviations. Implementation matches spec exactly.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/creature_core.rs` - New shared struct with 9 fields, apply_hp_delta, and Combatant impl
- `crates/sidequest-game/src/character.rs` - Refactored to embed `pub core: CreatureCore` with `#[serde(flatten)]`
- `crates/sidequest-game/src/npc.rs` - Refactored to embed `pub core: CreatureCore` with `#[serde(flatten)]`
- `crates/sidequest-game/src/lib.rs` - Added `creature_core` module and `CreatureCore` re-export

**Tests:** 94/94 passing (GREEN) — 89 original + 5 new CreatureCore tests
**Branch:** feat/1-13-creature-core (pushed)

**Handoff:** To review phase
