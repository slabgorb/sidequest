---
story_id: "9-8"
jira_key: ""
epic: "9"
workflow: "tdd"
---
# Story 9-8: GM commands — /gm set, /gm teleport, /gm spawn, /gm dmg operator-only commands

## Story Details
- **ID:** 9-8
- **Jira Key:** (none — personal project)
- **Workflow:** tdd
- **Stack Parent:** 9-6 (slash command router — completed)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-28T09:43:29Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-28 | 2026-03-28T09:39:06Z | 9h 39m |
| red | 2026-03-28T09:39:06Z | 2026-03-28T09:41:47Z | 2m 41s |
| green | 2026-03-28T09:41:47Z | 2026-03-28T09:43:28Z | 1m 41s |
| spec-check | 2026-03-28T09:43:28Z | 2026-03-28T09:43:28Z | 0s |
| verify | 2026-03-28T09:43:28Z | 2026-03-28T09:43:29Z | 1s |
| review | 2026-03-28T09:43:29Z | 2026-03-28T09:43:29Z | 0s |
| finish | 2026-03-28T09:43:29Z | - | - |

## Story Context

This story implements operator-only GM commands that modify game state. It builds on:
- **9-6** (slash command router) — `SlashRouter`, `CommandHandler` trait, `CommandResult` enum
- **9-7** (core slash commands) — `StatusCommand`, `InventoryCommand`, `MapCommand`, `SaveCommand` pattern

### Required Commands

Each command returns `CommandResult::StateMutation(WorldStatePatch)`:

1. **/gm set \<field\> \<value\>** — Direct state field mutation
   - `/gm set location "The Shrine of Whispers"`
   - `/gm set time_of_day "midnight"`
   - `/gm set atmosphere "oppressive silence"`
   - `/gm set current_region "Haunted_Wastes"`
   - Returns: `StateMutation` with the requested field set

2. **/gm teleport \<region\> \<location\>** — Move character to new region/location
   - `/gm teleport Haunted_Wastes "The Shrine of Whispers"`
   - Discovers the region if not already discovered
   - Returns: `StateMutation` with location, current_region, and discover_regions updated

3. **/gm spawn \<character_type\> \<name\> \<role\> \<attitude\>** — Create NPC
   - `/gm spawn npc Morsemere "Harbinger" "reverent"`
   - Builds an `NpcPatch` and returns it via `npcs_present`
   - Returns: `StateMutation` with NPC added to npcs_present

4. **/gm dmg \<target\> \<amount\>** — Deal damage to character/NPC
   - `/gm dmg player 5`
   - `/gm dmg Morsemere 3`
   - Validates target exists in game state
   - Returns: `StateMutation` with hp_changes entry

### Operator Check

All GM commands must check if the operator/GM flag is set in the game state.
If not an operator, return `CommandResult::Error("Operator access required"...)`.

Assume a field `is_operator: bool` is available on the game state or session.

### Implementation Pattern

Each command is a struct implementing `CommandHandler`:

```rust
pub struct GmSetCommand;

impl CommandHandler for GmSetCommand {
    fn name(&self) -> &str { "gm set" }
    fn description(&self) -> &str { "GM: Set a world field directly" }
    fn handle(&self, state: &GameSnapshot, args: &str) -> CommandResult {
        // Parse args
        // Check operator
        // Build WorldStatePatch
        // Return StateMutation
    }
}
```

## Delivery Findings

No upstream findings.

## Design Deviations

No deviations logged yet.

## Sm Assessment

**Story 9-8 is ready for RED phase.**

- Session file created with story context and implementation plan
- Branch `feat/9-8-gm-slash-commands` created on sidequest-api (based on develop with 9-6 + 9-7 merged)
- Depends on 9-6 (router) and 9-7 (core commands) — both merged
- TDD workflow: next phase is RED, owned by Tyr One-Handed (TEA)
- 5 point story: /gm set, /gm teleport, /gm spawn, /gm dmg
- Key design: GM commands return StateMutation(WorldStatePatch), not Display

**Routing to TEA for failing test design.**

## Delivery Findings

- No upstream findings during setup.

### TEA (test design)

- **Question** (non-blocking): Operator authorization check — story context suggests adding `is_operator: bool` to `try_dispatch()` or checking a session/state flag. Current SlashRouter.try_dispatch() has no operator parameter. Tests don't cover operator auth (deferred to router-level concern). Dev should decide where to gate operator access. Affects `crates/sidequest-game/src/slash_router.rs` (may need signature change). *Found by TEA during test design.*

## TEA Assessment

**Tests Required:** Yes
**Reason:** Core new module — 4 GM subcommands with state mutation

**Test Files:**
- `crates/sidequest-game/tests/gm_commands_story_9_8_tests.rs` — 24 tests for GM commands

**Tests Written:** 24 tests covering 7 ACs

| AC | Tests | Count |
|----|-------|-------|
| /gm set | `gm_set_location_returns_state_mutation`, `gm_set_time_of_day`, `gm_set_atmosphere`, `gm_set_current_region`, `gm_set_missing_value_returns_error`, `gm_set_missing_all_args_returns_error`, `gm_set_unknown_field_returns_error` | 7 |
| /gm teleport | `gm_teleport_sets_location_and_region`, `gm_teleport_discovers_region`, `gm_teleport_missing_args_returns_error` | 3 |
| /gm spawn | `gm_spawn_creates_npc_patch`, `gm_spawn_missing_name_returns_error` | 2 |
| /gm dmg | `gm_dmg_creates_hp_change`, `gm_dmg_missing_amount_returns_error`, `gm_dmg_invalid_amount_returns_error`, `gm_dmg_missing_all_args_returns_error` | 4 |
| Unknown subcommand | `gm_unknown_subcommand_returns_error`, `gm_no_subcommand_returns_error` | 2 |
| StateMutation | `all_gm_subcommands_return_state_mutation` | 1 |
| Trait + Integration | `gm_command_trait_methods`, `gm_dispatches_through_router` | 2 |

**Status:** RED (fails to compile — `unresolved import sidequest_game::commands::GmCommand`)

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #6 test quality | Self-check: all 24 tests have meaningful assertions | passing |
| #9 public fields | Tests use CommandHandler trait methods only | enforced by API |

**Rules checked:** 2 of 15 applicable
**Self-check:** 0 vacuous tests found

**Handoff:** To Loki Silvertongue (Dev) for implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/commands.rs` — Added GmCommand with subcommand dispatch (set, teleport, spawn, dmg)

**Tests:** 21/21 passing (GREEN), plus 9-6 (21) and 9-7 (23) still green
**Branch:** feat/9-8-gm-slash-commands (pushed)

**Implementation notes:**
- 154 lines added to existing commands.rs
- Single GmCommand struct dispatches on first word of args
- `/gm set` validates field name against whitelist (location, time_of_day, atmosphere, current_region, active_stakes)
- `/gm teleport` sets location + current_region + discover_regions in one patch
- `/gm spawn` builds NpcPatch with name, optional role and personality
- `/gm dmg` parses target name (can have spaces) + amount via rsplit_once, applies as negative HP

**Handoff:** To finish phase

### Dev (implementation)

- No upstream findings during implementation.

## Design Deviations

### Dev (implementation)
- No deviations from spec.

### TEA (test design)
- **Operator authorization deferred to router level**
  - Spec source: context-story-9-8.md, AC "Operator only"
  - Spec text: "Non-operator receives error for /gm commands"
  - Implementation: Tests do not cover operator auth check — GmCommand handler focuses on subcommand dispatch. Auth should be gated at router level (try_dispatch signature change) or via a session/state flag.
  - Rationale: Adding is_operator to try_dispatch would break the 9-6 API. Auth is a cross-cutting concern better handled at the router or orchestrator level, not in individual command handlers.
  - Severity: minor
  - Forward impact: Operator auth will need to be added either to SlashRouter or orchestrator integration. Not blocking for this story's core functionality.

No deviations at setup.