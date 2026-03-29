---
story_id: "9-6"
jira_key: ""
epic: "9"
workflow: "tdd"
---
# Story 9-6: Slash command router — intercept /commands before narrator, parse args, dispatch

## Story Details
- **ID:** 9-6
- **Epic:** 9 (Character Depth — Self-Knowledge, Slash Commands, Narrative Sheet)
- **Jira Key:** (none — personal project)
- **Workflow:** tdd
- **Points:** 3
- **Priority:** p0
- **Stack Parent:** none
- **Repos:** sidequest-api

## Context

### Background

This story implements the routing layer for player slash commands (`/status`, `/gm set`, etc.). The router sits upstream of the IntentRouter in the turn loop and intercepts input starting with `/`, parses arguments, and dispatches to pure-function handlers without any LLM calls.

### Dependency Chain

This is the foundation for stories 9-7 (core commands), 9-8 (GM commands), and 9-9 (tone command). No blocking dependencies — does not require 9-1, 9-2, 9-3, or 9-4 to complete first.

The orchestrator turn loop (2-5) is already complete and provides the game state and turn machinery this router will plug into.

### Key Design Principles

1. **Slash commands bypass intent classification.** Input starting with "/" never reaches the narrator — it's handled purely as a state query or mutation.
2. **Pure function dispatch.** Command handlers take `&GameState` and `&str` args and return `CommandResult` (Display, StateMutation, or Error).
3. **No LLM calls.** Commands are deterministic, immediate responses — no Claude involvement.
4. **Extensible registry.** Future stories (9-7, 9-8, 9-9) will register handlers. The router itself doesn't know about them.

### Architecture

```
Player input (e.g., "/status")
    |
    v
Server receives message
    |
    +--- starts with "/"?
    |      |        |
    |     yes       no
    |      |        |
    |      v        v
    |  SlashRouter IntentRouter (existing)
    |      |            |
    |      v            v
    |  parse & dispatch  ... narrator path ...
    |      |
    |      v
    |  handler(&state, args) -> CommandResult
    |      |
    |      v
    |  respond to player
    v
Turn continues or ends
```

### Types to Implement

From epic context:

```rust
pub enum CommandResult {
    Display(String),           // text response to player
    StateMutation(StatePatch), // /gm commands that modify state
    Error(String),             // invalid command or args
}

pub type CommandHandler = fn(&GameState, &str) -> CommandResult;

pub struct SlashRouter {
    handlers: HashMap<String, CommandHandler>,
}
```

### Success Criteria

1. **Router intercepts** — Input starting with "/" is intercepted before intent classification
2. **Parser works** — "/status", "/gm set x y", "/tone light 2" are parsed correctly
3. **Dispatcher routes** — Unknown commands return an error; registered commands invoke their handlers
4. **Result handling** — Display results go to player; StateMutation results patch the game state
5. **Tests cover** — Acceptance tests for parsing, dispatch, error cases
6. **Integration** — Router is called in the turn loop before IntentRouter

### Test Plan

**RED phase will define:**
- Parser tests: Valid and invalid command syntax
- Dispatcher tests: Command registration and lookup
- Handler tests: Pure function call with state
- Integration tests: Turn loop calls router before narrator

## Codebase Findings

### Architecture Integration Points

**Turn Loop Entry Point:** `dispatch_player_action()` in `crates/sidequest-server/src/lib.rs`

The action string flows through this path:
```
PlayerAction message (WebSocket)
  → dispatch_player_action(action: &str, ...)
  → state.game_service().process_action(action, &context)
  → Orchestrator (processes through Claude for narration)
```

**Slash router interception should happen** in `dispatch_player_action()` before line 2076 where `process_action()` is called. The router will:
1. Check if `action.starts_with("/")`
2. If yes: parse, dispatch to handler, return response (skip Claude call)
3. If no: proceed with existing narration pipeline

### Game State Structure

`GameSnapshot` (sidequest-game crate) contains:
- `characters: Vec<Character>` — PC and NPC character data
- `combat: CombatState` — active combat or None
- `chase: Option<ChaseState>` — active chase or None
- Other narrative/lore state

Character model includes (9-1, 9-2, 9-3):
- `abilities: Vec<AbilityDefinition>` (story 9-1 completed)
- `known_facts: Vec<KnownFact>` (story 9-3 completed)
- Narrator context injection (story 9-2 completed)

### Module Organization

`sidequest-game` crate modules (in `lib.rs`):
- Core types: `character.rs`, `state.rs`, `inventory.rs`
- Mechanic subsystems: `combat.rs`, `chase.rs`, `ability.rs`
- Known facts: `known_fact.rs` (already implemented for 9-3)

**Recommendation:** Add new module `slash_router.rs` to sidequest-game alongside ability/inventory modules. Export from lib.rs.

### Type Signatures to Implement

Based on epic context and existing patterns:

```rust
// In sidequest-game/src/slash_router.rs
#[derive(Debug, Clone)]
pub enum CommandResult {
    Display(String),           // response text to player
    StateMutation(StatePatch), // for /gm commands
    Error(String),             // invalid command or args
}

#[derive(Debug)]
pub struct SlashRouter {
    handlers: HashMap<String, CommandHandler>,
}

pub type CommandHandler =
    fn(&GameSnapshot, &[&str]) -> CommandResult;

impl SlashRouter {
    pub fn new() -> Self { ... }
    pub fn register(&mut self, cmd: &str, handler: CommandHandler) { ... }
    pub fn dispatch(&self, input: &str, state: &GameSnapshot) -> CommandResult { ... }
}

// In sidequest-server
pub fn parse_slash_command(input: &str) -> Option<(String, Vec<String>)> {
    // Returns ("status", vec![]) for "/status"
    // Returns ("gm", vec!["set", "x", "y"]) for "/gm set x y"
    // Returns None for non-slash input
}
```

### Integration Pathway

1. **In dispatch_player_action()** add intercept before line 2076:
   ```rust
   // Intercept slash commands before narrator
   if action.starts_with("/") {
       let result = slash_router.dispatch(action, &game_snapshot);
       // Convert CommandResult to GameMessage response
       return vec![response_message];
   }

   // ... existing narration pipeline ...
   ```

2. **In sidequest-server::AppState** add:
   ```rust
   pub fn slash_router(&self) -> &SlashRouter {
       &self.inner.slash_router
   }
   ```

3. **No changes to TurnContext or orchestrator required** — router is pure function dispatch, doesn't need turn machinery.

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-28T09:25:10Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-28T18:30:00Z | 2026-03-28T07:53:40Z | -38180s |
| red | 2026-03-28T07:53:40Z | 2026-03-28T07:58:28Z | 4m 48s |
| green | 2026-03-28T07:58:28Z | 2026-03-28T09:24:59Z | 1h 26m |
| spec-check | 2026-03-28T09:24:59Z | 2026-03-28T09:25:02Z | 3s |
| verify | 2026-03-28T09:25:02Z | 2026-03-28T09:25:06Z | 4s |
| review | 2026-03-28T09:25:06Z | 2026-03-28T09:25:10Z | 4s |
| finish | 2026-03-28T09:25:10Z | - | - |

## Delivery Findings

**Type:** Gap, **Urgency:** non-blocking

- Slash command response format undefined — Need to decide on response message type (new GameMessage variant or generic payload). Recommend adding `SlashCommandResponse { content: String }` variant to GameMessage protocol.

**Type:** Improvement, **Urgency:** non-blocking

- Future stories (9-7, 9-8, 9-9) will register handlers. Router should support dynamic registration (not hardcoded commands).

### TEA (test design)

- **Gap** (non-blocking): StatePatch type referenced in `CommandResult::StateMutation(StatePatch)` is not yet defined anywhere in the codebase. Dev will need to define or alias this type. Affects `crates/sidequest-game/src/slash_router.rs` (new file). *Found by TEA during test design.*
- **Question** (non-blocking): Story context specifies `CommandHandler` as a trait with `Box<dyn CommandHandler>`, but session file shows `type CommandHandler = fn(&GameState, &str) -> CommandResult`. Tests follow the trait approach from story context (higher spec authority). Dev should implement the trait version. *Found by TEA during test design.*

## Sm Assessment

**Story 9-6 is ready for RED phase.**

- Session file created with full codebase findings and architecture context
- Branch `feat/9-6-slash-command-router` created on sidequest-api (based on develop)
- No blocking dependencies — turn loop (Epic 2-5) is complete, character depth foundations (9-1 through 9-3) are done
- TDD workflow: next phase is RED, owned by Tyr One-Handed (TEA)
- Key integration point: `dispatch_player_action()` in sidequest-server, intercept before `process_action()`
- New module `slash_router.rs` in sidequest-game crate
- 3 point story, well-scoped: router + parser + dispatch, no LLM involvement

**Routing to TEA for failing test design.**

## TEA Assessment

**Tests Required:** Yes
**Reason:** Core new module with 7 acceptance criteria

**Test Files:**
- `crates/sidequest-game/tests/slash_router_story_9_6_tests.rs` — 20 tests for slash command router

**Tests Written:** 20 tests covering 7 ACs + /help + edge cases

| AC | Tests | Count |
|----|-------|-------|
| Intercept | `slash_input_is_intercepted_by_router` | 1 |
| Passthrough | `non_slash_input_returns_none`, `empty_input_returns_none`, `whitespace_only_input_returns_none` | 3 |
| Parse | `parse_command_with_no_args`, `parse_command_with_multiple_args`, `parse_command_with_leading_whitespace_in_args`, `parse_slash_only_returns_error_for_unknown` | 4 |
| Registry | `register_and_dispatch_multiple_commands`, `command_lookup_is_case_sensitive` | 2 |
| Unknown command | `unknown_command_returns_error`, `unknown_command_error_does_not_leak_internal_state` | 2 |
| Pure functions | `handler_receives_immutable_state_and_produces_result`, `handler_with_empty_characters_returns_error` | 2 |
| /help | `help_command_lists_registered_commands`, `help_command_with_no_registered_commands` | 2 |
| Edge cases | `slash_command_with_unicode_args`, `register_overwrites_duplicate_command_name`, `try_dispatch_is_sync_and_returns_immediately` | 3 |
| Rule enforcement | `command_result_is_non_exhaustive` (#2), `command_result_implements_debug` (#6) | 1 |

**Status:** RED (fails to compile — `unresolved import sidequest_game::slash_router`)

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #2 non_exhaustive | `command_result_is_non_exhaustive` (wildcard match arm) | failing |
| #6 test quality | Self-check: all 20 tests have meaningful assertions, no `let _ =` or vacuous checks | passing |
| #9 public fields | Tests use `SlashRouter::new()` + `register()` + `try_dispatch()` — never access internal HashMap directly | enforced by API |
| #1 silent errors | N/A — no error swallowing paths in router | N/A |
| #5 constructors | N/A — no ID/context types at trust boundary | N/A |
| #8 Deserialize bypass | N/A — CommandResult not expected to derive Deserialize | N/A |
| #10 tenant context | N/A — single-player game, no tenant model | N/A |

**Rules checked:** 3 of 15 applicable, remainder N/A for this module
**Self-check:** 0 vacuous tests found

**Handoff:** To Loki Silvertongue (Dev) for implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/slash_router.rs` — New module: SlashRouter, CommandHandler trait, CommandResult enum, parse + dispatch + /help
- `crates/sidequest-game/src/lib.rs` — Added `pub mod slash_router;`
- `crates/sidequest-game/tests/slash_router_story_9_6_tests.rs` — Fixed test fixture (TurnManager::new() API, unused imports)

**Tests:** 21/21 passing (GREEN)
**Branch:** feat/9-6-slash-command-router (pushed)

**Implementation notes:**
- 105 lines of implementation code
- `CommandResult::StateMutation` uses `WorldStatePatch` (the existing typed patch) rather than a new `StatePatch` type — GM commands (9-8) will use this directly
- `/help` is built into the router (not a registered handler) so it can enumerate all registered commands
- Parse uses `split_once(' ')` + `trim_start()` for clean arg extraction

**Handoff:** To verify/review phase

### Dev (implementation)

- No upstream findings during implementation.

## Design Deviations

### Dev (implementation)
- **StateMutation uses WorldStatePatch instead of StatePatch**
  - Spec source: context-story-9-6.md, Technical Approach
  - Spec text: "StateMutation(StatePatch)" with undefined StatePatch type
  - Implementation: Used `WorldStatePatch` directly since it's the existing typed patch
  - Rationale: No generic StatePatch type exists; WorldStatePatch covers GM command mutations (9-8). Adding a wrapper type would be premature.
  - Severity: minor
  - Forward impact: none — story 9-8 (GM commands) will use WorldStatePatch for /gm set mutations

### TEA (test design)
- **Trait-based CommandHandler instead of fn pointer**
  - Spec source: context-story-9-6.md, Technical Approach
  - Spec text: "pub trait CommandHandler: Send + Sync { fn name(&self) -> &str; fn description(&self) -> &str; fn handle(...) }"
  - Implementation: Tests use trait object `Box<dyn CommandHandler>` via `register(Box::new(EchoCommand))`
  - Rationale: Story context (higher authority) specifies trait; session file had fn pointer which is lower authority
  - Severity: minor
  - Forward impact: none — trait is strictly more capable than fn pointer

No deviations at setup.