---
story_id: "45-8"
jira_key: null
epic: "45"
workflow: "wire-first"
---
# Story 45-8: Notorious-party gating on session player_count

## Story Details
- **ID:** 45-8
- **Jira Key:** (not yet created)
- **Epic:** 45
- **Workflow:** wire-first
- **Priority:** P1
- **Type:** bug
- **Points:** 2
- **Repos:** server
- **Stack Parent:** none

## Problem Statement

Playtest 3 (2026-04-19) evropi session revealed a critical narrative isolation failure: Rux (a named party member in the full-party context) leaked into pumblestone_sweedlewit's solo session narrative prose. The narrator referenced Rux by name despite pumblestone being the only player in the active session.

**Root cause:** The world configuration seeds a known-party context via the `notorious_party` fixture regardless of actual session player count. In a solo session, the narrator receives full party context and inadvertently weaves other characters into narration intended for a solo player.

**Impact:** Solo players see reference to named party members who aren't present, breaking narrative consistency and creating confusion about who is actually in the session.

## Acceptance Criteria

### AC1: Solo Session Isolation Gate
When `session.player_count == 1`, the `notorious_party` context seed must be completely gated out of the narrator prompt context. Verify via grep that no part of the party-member fixture reaches the prompt-building path for solo sessions.

### AC2: Multiplayer Passthrough
When `session.player_count > 1`, the `notorious_party` context continues to seed normally. Verify existing multiplayer tests confirm narration references the full party.

### AC3: OTEL Observability
Emit an OTEL span on the gating decision showing:
- `session.player_count` (actual count)
- `notorious_party_gated` (boolean: true if gated out)
- `party_context_available` (boolean: true if included in prompt context)

The span must fire on every turn so the GM panel shows when the gate is active.

### AC4: No Silent Fallbacks
If the gating mechanism is missing or broken, narrator invocation must fail loud with an OTEL event and structured log—never silently proceed with wrong context.

### AC5: Wiring Test
Write a RED-phase boundary test that:
- Spins up a solo session (player_count=1) with known world config containing notable named NPCs
- Triggers a turn and captures the narrator prompt context
- Asserts that no named party member from the notorious_party fixture appears in the prompt
- Confirms AC3 OTEL span fires with `notorious_party_gated=true`

Add a complementary multiplayer test that verifies the party context IS included when player_count > 1.

## Workflow Tracking
**Workflow:** wire-first
**Phase:** setup
**Phase Started:** 2026-04-28T16:47:10Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-28T16:47:10Z | - | - |

## Technical Investigation

### Delivery Findings

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Design Deviations

No deviations logged.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

## Branch & Repository

**Repository:** sidequest-server
**Branch:** feat/45-8-notorious-party-gating-player-count
**Workflow Type:** phased (wire-first)
