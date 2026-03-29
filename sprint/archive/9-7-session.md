---
story_id: "9-7"
jira_key: ""
epic: "9"
workflow: "tdd"
---
# Story 9-7: Core slash commands — /status, /inventory, /map, /save implementations

## Story Details
- **ID:** 9-7
- **Epic:** 9 (Character Depth — Self-Knowledge, Slash Commands, Narrative Sheet)
- **Workflow:** tdd
- **Points:** 5
- **Stack Parent:** 9-6 (Slash command router)
- **Repos:** sidequest-api

## Acceptance Criteria

| AC | Detail |
|----|--------|
| /status | Returns character HP, level, class, race, location |
| /inventory | Lists equipped items and pack contents with gold |
| /inventory empty | Empty inventory returns flavor text, not empty string |
| /map | Shows discovered regions with current marked, routes |
| /save | Returns confirmation message |
| No LLM | All commands resolve without Claude calls |
| Error handling | Missing character produces clear error messages |

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-28T09:36:51Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-28 | 2026-03-28 | instant |
| red | 2026-03-28T09:31:24Z | 2026-03-28T09:34:57Z | 3m 33s |
| green | 2026-03-28T09:34:57Z | 2026-03-28T09:36:51Z | 1m 54s |
| spec-check | 2026-03-28T09:36:51Z | 2026-03-28T09:36:51Z | 0s |
| verify | 2026-03-28T09:36:51Z | 2026-03-28T09:36:51Z | 0s |
| review | 2026-03-28T09:36:51Z | 2026-03-28T09:36:51Z | 0s |
| finish | 2026-03-28T09:36:51Z | - | - |

## Delivery Findings

- No upstream findings during setup.

### TEA (test design)

- **Gap** (non-blocking): Branch `feat/9-7-core-slash-commands` was created before 9-6 merged to develop. Dev needs to rebase onto develop to get `slash_router` module. Affects `crates/sidequest-game/` (rebase needed). *Found by TEA during test design.*

## TEA Assessment

**Tests Required:** Yes
**Reason:** Core new module with 7 acceptance criteria, 4 command handler implementations

**Test Files:**
- `crates/sidequest-game/tests/slash_commands_story_9_7_tests.rs` — 24 tests for core slash commands

**Tests Written:** 24 tests covering 7 ACs

| AC | Tests | Count |
|----|-------|-------|
| /status | `status_displays_character_name_and_hp`, `status_displays_level_class_race`, `status_displays_location`, `status_with_no_character_returns_error`, `status_with_zero_hp_still_displays` | 5 |
| /inventory | `inventory_lists_equipped_items`, `inventory_lists_pack_contents`, `inventory_separates_equipped_from_pack`, `inventory_shows_gold`, `inventory_empty_returns_flavor_text`, `inventory_no_character_returns_error` | 6 |
| /map | `map_lists_all_discovered_regions`, `map_marks_current_region`, `map_lists_discovered_routes`, `map_no_regions_returns_meaningful_text` | 4 |
| /save | `save_returns_confirmation`, `save_is_deterministic` | 2 |
| Pure functions | `all_commands_are_sync` | 1 |
| Integration | `all_four_commands_dispatch_through_router` | 1 |
| Trait compliance | `status_command_trait_methods`, `inventory_command_trait_methods`, `map_command_trait_methods`, `save_command_trait_methods` | 4 |

**Status:** RED (fails to compile — `unresolved import sidequest_game::commands`)

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #6 test quality | Self-check: all 24 tests have meaningful assertions | passing |
| #9 public fields | Tests use CommandHandler trait methods only — no direct field access | enforced by API |
| #2 non_exhaustive | N/A — no new enums in this story (CommandResult from 9-6) | N/A |

**Rules checked:** 2 of 15 applicable
**Self-check:** 0 vacuous tests found

**Handoff:** To Loki Silvertongue (Dev) for implementation

## Sm Assessment

**Story 9-7 is ready for RED phase.**

- Session file created with story context and implementation plan
- Branch `feat/9-7-core-slash-commands` created on sidequest-api
- Depends on 9-6 (slash command router) which is now merged
- TDD workflow: next phase is RED, owned by Tyr One-Handed (TEA)
- 5 point story: /status, /inventory, /map, /save command handlers

**Routing to TEA for failing test design.**

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/commands.rs` — New module: StatusCommand, InventoryCommand, MapCommand, SaveCommand
- `crates/sidequest-game/src/lib.rs` — Added `pub mod commands;`

**Tests:** 23/23 passing (GREEN), plus 21/21 from 9-6 still green
**Branch:** feat/9-7-core-slash-commands (pushed)

**Implementation notes:**
- 164 lines, single-file module (flat structure matching crate convention)
- Equipped/pack item separation with descriptions for equipped, names for pack
- Gold display at bottom of inventory
- Current region marked with `*` prefix in map output
- Flavor text for empty inventory ("Your pockets are as empty as the wasteland")
- Error handling for missing characters on /status and /inventory

**Handoff:** To finish phase

### Dev (implementation)

- No upstream findings during implementation.

## Design Deviations

### Dev (implementation)
- **Save returns Display instead of StateMutation**
  - Spec source: context-story-9-7.md, Technical Approach
  - Spec text: "`/save` is the only command that produces a `StateMutation` result"
  - Implementation: Returns `CommandResult::Display` with confirmation text
  - Rationale: Tests expect `Display` variant. Actual persistence will be wired in orchestrator integration (not this story's scope). The save handler signals intent; the orchestrator acts on it.
  - Severity: minor
  - Forward impact: none — orchestrator integration is a separate concern

### TEA (test design)
- No deviations from spec.