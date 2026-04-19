---
story_id: "7-9"
jira_key: null
epic: "7"
workflow: "tdd"
---

# Story 7-9: ScenarioEngine integration — wire scenario lifecycle into orchestrator turn loop

## Story Details

- **ID:** 7-9
- **Epic:** 7 (Scenario System — Bottle Episodes, Whodunit, Belief State)
- **Title:** ScenarioEngine integration — wire scenario lifecycle into orchestrator turn loop
- **Jira Key:** None (personal project, no Jira)
- **Workflow:** tdd (Test-Driven Development)
- **Stack Parent:** 7-5 (NPC autonomous actions) — completed
- **Points:** 5
- **Priority:** p2
- **Repos:** sidequest-api (gitflow, develop base)

## Story Context

This is the integration story for the Scenario System (Epic 7). Stories 7-1 through 7-8 have implemented the core scenario mechanics:

- **7-1**: BeliefState model (per-NPC knowledge bubbles)
- **7-2**: Gossip propagation (claims, credibility decay)
- **7-3**: Clue activation (semantic triggers)
- **7-4**: Accusation system (evidence evaluation)
- **7-5**: NPC autonomous actions (alibi, confess, flee, destroy evidence)
- **7-6**: Scenario pacing (tension escalation)
- **7-7**: Scenario archiver (save/resume state)
- **7-8**: Scenario scoring (evidence metrics, deduction quality)

**7-9 connects these subsystems into the game loop.** The ScenarioState struct already exists in `sidequest-game`, and the dispatcher infrastructure is in place. This story wires:

1. **Scenario lifecycle into turn loop** — bind ScenarioPack → ScenarioState at session start
2. **Between-turn processing** — gossip propagation, NPC autonomous actions, clue evaluation after each turn
3. **OTEL observability** — spans for scenario decisions (clue discovery, NPC actions, accusations)
4. **Integration tests** — verify the full wiring from dispatcher to scenario engine to game state mutations

### Key System Dependencies

- **ScenarioState** — `sidequest-game/src/scenario_state.rs` — runtime state binding genre pack to game session
- **GameSnapshot::scenario_state** — `sidequest-game/src/state.rs` — field already exists, optional
- **DispatchContext** — `sidequest-server/src/dispatch/mod.rs` — turn loop context (needs scenario_state field)
- **TurnContext** — `sidequest-agents/src/orchestrator.rs` — agent orchestrator (may need scenario event injection)

### Specification

#### Acceptance Criteria

1. **AC1:** ScenarioState is initialized from genre pack's ScenarioPack when a scenario world begins
   - If genre pack has scenarios, load first scenario at session start
   - Deserialize from saved state on session resume
2. **AC2:** Between-turn processing fires after narrator resolves each turn
   - Gossip engine propagates claims
   - NPC autonomous actions evaluated (via `select_npc_action()`)
   - Clue activation checked (via `ClueActivation::evaluate()`)
   - ScenarioEvents collected for narrator context injection
3. **AC3:** Accusation handling in dispatcher
   - Player /accuse command detected
   - Evidence evaluated via `evaluate_accusation()`
   - Result triggers scenario resolution or continuation
4. **AC4:** OTEL observability
   - Agent span: `scenario:advance` on between-turn processing
   - Event: `scenario:clue_discovered` when ClueActivation fires
   - Event: `scenario:npc_action` for autonomous actions
   - Event: `scenario:gossip_spread` for claim propagation
   - Event: `scenario:accusation_resolved` with result (Guilty/Innocent/Insufficient)
5. **AC5:** Full integration test
   - Load a whodunit scenario from test genre pack
   - Verify scenario_state initializes
   - Advance turn, verify gossip events logged
   - Trigger accusation, verify resolution path taken
   - Verify OTEL spans visible in test harness

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-07T11:53:17Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-07T07:20Z | 2026-04-07T11:15:52Z | 3h 55m |
| red | 2026-04-07T11:15:52Z | 2026-04-07T11:25:50Z | 9m 58s |
| green | 2026-04-07T11:25:50Z | 2026-04-07T11:38:32Z | 12m 42s |
| spec-check | 2026-04-07T11:38:32Z | 2026-04-07T11:47:42Z | 9m 10s |
| verify | 2026-04-07T11:47:42Z | 2026-04-07T11:47:50Z | 8s |
| review | 2026-04-07T11:47:50Z | 2026-04-07T11:53:12Z | 5m 22s |
| spec-reconcile | 2026-04-07T11:53:12Z | 2026-04-07T11:53:17Z | 5s |
| finish | 2026-04-07T11:53:17Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): `sidequest-game/CLAUDE.md` "NOT STARTED" section still lists "Scenario system — Epic 7" as having no code, but 7-1 through 7-8 are all merged. The CLAUDE.md is stale.
  Affects `crates/sidequest-game/CLAUDE.md` (update feature inventory).
  *Found by TEA during test design.*
- **Improvement** (non-blocking): Existing NPC action OTEL in `dispatch/mod.rs:498-507` uses `"npc_actions"` WatcherEvent prefix rather than the `"scenario"` namespace. AC4 wants unified `scenario:*` namespace for GM panel filtering. Dev should migrate the existing events during OTEL standardization.
  Affects `crates/sidequest-server/src/dispatch/mod.rs` (rename OTEL prefix).
  *Found by TEA during test design.*

### Dev (implementation)
- No upstream findings during implementation.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

## Sm Assessment

Story 7-9 is the capstone integration story for Epic 7 (Scenario System). All eight prerequisite stories (7-1 through 7-8) are complete and merged to develop. The scenario subsystems — belief state, gossip, clues, accusations, NPC actions, pacing, archiver, and scoring — are fully implemented but not wired into the orchestrator turn loop.

**Routing:** TEA (Fezzik) for RED phase. Write failing integration tests that verify:
1. ScenarioState initialization from genre pack at session start
2. Between-turn processing (gossip, NPC actions, clue activation)
3. Accusation handling through dispatcher
4. OTEL span emission for scenario decisions
5. Full lifecycle integration test

This is a wiring story — the pieces exist, they need to be connected. TEA should focus tests on verifying the wiring points, not re-testing the individual subsystems (those are covered by 7-1 through 7-8 tests).

## Tea Assessment

**Tests Required:** Yes
**Reason:** Capstone wiring story — must verify all 5 ACs connect subsystems to dispatch pipeline

**Test Files:**
- `crates/sidequest-server/tests/scenario_integration_story_7_9_tests.rs` — 17 tests covering all 5 ACs

**Tests Written:** 17 tests covering 5 ACs
**Status:** RED (8 failing, 9 passing — ready for Dev)

### Failing Tests (Dev must fix)

| Test | AC | Gap |
|------|----|-----|
| `prompt_builder_injects_scenario_context` | AC2 | prompt.rs has zero scenario references |
| `accuse_command_routed_to_scenario` | AC3 | No /accuse command in slash router or dispatch |
| `accusation_result_triggers_resolution` | AC3 | No AccusationResult processing in dispatch |
| `otel_scenario_advance_span_exists` | AC4 | No scenario:advance span wrapping between-turn |
| `otel_clue_discovered_event_exists` | AC4 | No clue_discovered OTEL event |
| `otel_gossip_spread_event_exists` | AC4 | No gossip_spread OTEL event |
| `otel_accusation_resolved_event_exists` | AC4 | No accusation_resolved OTEL event |
| `scenario_lifecycle_fully_wired` | AC5 | Composite — fails on prompt + accusation + OTEL gaps |

### Passing Tests (Already wired)

| Test | AC | What's wired |
|------|----|-------------|
| `scenario_state_importable_from_server_crate` | AC1 | Types reachable |
| `connect_handler_initializes_scenario_state` | AC1 | Init in connect.rs |
| `scenario_state_serde_roundtrip` | AC1 | Save/restore |
| `dispatch_calls_process_between_turns` | AC2 | Between-turn fires |
| `scenario_events_injected_into_prompt_context` | AC2 | Events flow |
| `otel_npc_action_event_uses_scenario_namespace` | AC4 | NPC OTEL present |
| `game_snapshot_scenario_state_roundtrip` | AC5 | State persistence |
| `all_scenario_types_reachable_from_server` | Wiring | All types importable |
| `accusation_types_importable` | AC3 | Types exist |

### Rule Coverage

No lang-review rules file exists for Rust. Tests enforce project rules:

| Rule | Test(s) | Status |
|------|---------|--------|
| Wiring test required | `scenario_lifecycle_fully_wired` | failing (expected) |
| OTEL observability | 5 OTEL-specific tests | 4 failing, 1 passing |
| No silent fallbacks | All assertions fail loudly with descriptive messages | enforced |
| Verify wiring not just existence | Source-level checks verify call sites, not just imports | enforced |

**Rules checked:** 4 project rules have test coverage
**Self-check:** 0 vacuous tests found. All tests have meaningful assertions.

### Dev Guidance (for Inigo Montoya)

Three areas need wiring:
1. **prompt.rs** — Add `format_narrator_context()` call or inject `scenario_state` into state_summary
2. **slash.rs or mod.rs** — Add `/accuse` command that calls `ScenarioState::handle_accusation()`
3. **mod.rs** — Add OTEL spans: `scenario:advance` (wrapping between-turn), `clue_discovered`, `gossip_spread`, `accusation_resolved`

All subsystem code exists in `sidequest-game/src/scenario_*.rs`. This is pure wiring — no new algorithms needed.

**Handoff:** To Inigo Montoya (Dev) for implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-server/src/dispatch/mod.rs` — OTEL namespace migration from "npc_actions" to "scenario", added scenario.advance span wrapping between-turn processing, specific events for gossip_spread and clue_discovered
- `crates/sidequest-server/src/dispatch/prompt.rs` — Added format_narrator_context() injection for scenario tension, discovered clues, and NPC suspicions
- `crates/sidequest-server/src/dispatch/slash.rs` — Added /accuse command routing to ScenarioState::handle_accusation() with evidence evaluation, resolution, and OTEL accusation_resolved event
- `crates/sidequest-server/src/dispatch/mod.rs` (test) — Updated pre-existing OTEL assertion to match new namespace

**Tests:** 17/17 passing (GREEN)
**Branch:** feat/7-9-scenario-engine-integration (pushed)

**Pre-existing failures:** `lore_char_creation_story_15_10_tests` (2 tests) — unrelated to this story, existed before changes.

**Handoff:** To next phase (verify)

## Reviewer Assessment

**Verdict:** REQUEST CHANGES — 2 blocking fixes required in slash.rs

**PR:** #341 (draft)

### Blocking Issues

1. **Phantom NPC accusation permanently resolves scenario (slash.rs:86-103)**
   `accused_npc_name` is not validated against the NPC roster before calling `handle_accusation()`. A typo (`/accuse Mayr` instead of `/accuse Mayor`) permanently marks the scenario resolved against a non-existent NPC. Irreversible state corruption.
   **Fix:** Validate `ctx.snapshot.npcs.iter().any(|n| n.core.name.as_str() == accused_npc_name)` before calling `handle_accusation()`. Return a user error listing valid NPC names if no match.

2. **No re-accusation guard (slash.rs:101)**
   `handle_accusation()` is called even when `scenario.is_resolved()` is already true. Allows duplicate accusation_resolved OTEL events and redundant state mutation.
   **Fix:** Add `if scenario.is_resolved() { return "Scenario already resolved" error }` before `handle_accusation()`.

### Non-Blocking Notes (accept as-is, improve later)

3. `/accuse` prefix matching too broad — `starts_with("/accuse")` matches `/accused`. Low risk (no other `/accuse*` commands exist). Could tighten to exact match + space.
4. Multi-word NPC names broken by `splitn(3, ' ')`. Parsing design choice — could use quoted tokens or slug-based names. Not a regression.
5. `_ => {}` wildcard swallows AccusationResolved variant in mod.rs event loop. Safe today since `process_between_turns` never emits it, but fragile.
6. Tension pre/post mismatch between scenario.advance span field and summary event. Cosmetic telemetry discrepancy.

### OTEL & Wiring

All 7 OTEL events verified under unified `"scenario"` namespace. Wiring check passed — all code paths in production functions. prompt.rs injection correctly guarded by `is_resolved()`.

**Handoff:** Back to Dev for the 2 blocking fixes, then re-review.

## References

- **ADR-030:** Scenario Packs — genre pack format, whodunit structure, gossip model
- **ADR-053:** Scenario System — belief state, gossip mechanics, clue activation semantics
- **sq-2 reference:** `sidequest/scenario/*.py` in archived codebase
- **Implementation reference:** `sidequest-game/src/scenario_*.rs` (7-1 through 7-8 implementations)
- **Dispatcher reference:** `sidequest-server/src/dispatch/mod.rs` — turn loop entry points