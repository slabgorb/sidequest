---
story_id: "19-5"
jira_key: "none"
epic: "19"
workflow: "tdd"
---
# Story 19-5: Consumable item depletion — uses_remaining on items, decrement on room transition

## Story Details
- **ID:** 19-5
- **Title:** Consumable item depletion — uses_remaining on items, decrement on room transition
- **Jira Key:** none (personal project)
- **Workflow:** tdd
- **Repos:** sidequest-api
- **Stack Parent:** none

## Story Context

During the Caverns & Claudes playtest, the narrator improvised resource pressure beautifully—torches burning down, rations consumed—but there was zero mechanical backing. This story adds the mechanical foundation for consumable depletion.

**Technical Scope:**
- Add `uses_remaining: Option<u32>` to Item struct in inventory.rs
- Implement `consume_use(item_id)` method that decrements and removes item at 0
- On room transition in room_graph mode, decrement `uses_remaining` for the first active item with tag 'light'
- Fire GameMessage when a light source is exhausted
- Genre pack `item_catalog` entries set `resource_ticks` as initial `uses_remaining`

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-04T10:13:58Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-04T00:00:00Z | 2026-04-04T09:31:34Z | 9h 31m |
| red | 2026-04-04T09:31:34Z | 2026-04-04T09:39:37Z | 8m 3s |
| green | 2026-04-04T09:39:37Z | 2026-04-04T10:09:57Z | 30m 20s |
| spec-check | 2026-04-04T10:09:57Z | 2026-04-04T10:12:43Z | 2m 46s |
| review | 2026-04-04T10:12:43Z | 2026-04-04T10:13:58Z | 1m 15s |
| finish | 2026-04-04T10:13:58Z | - | - |

## Sm Assessment

Story 19-5 is well-specified and directly addresses playtest findings from the Caverns & Claudes headless session. The `resource_ticks` field already exists in genre pack item catalogs — this story wires it into the engine. Branch `feat/19-5-consumable-item-depletion` created from develop in sidequest-api. No blockers, no dependencies. Ready for TEA to write failing tests.

## TEA Assessment

**Tests Required:** Yes
**Test Files:** `crates/sidequest-game/src/inventory.rs` — 18 new tests
**Tests Written:** 18 tests covering 5 ACs
**Status:** GREEN at unit level (pre-implemented methods had zero test coverage)
**Handoff:** To Dev for wiring implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-genre/src/models.rs` — added `resource_ticks: Option<u32>` to CatalogItem
- `crates/sidequest-server/src/dispatch/connect.rs` — wire `catalog_item.resource_ticks` → `uses_remaining` during item construction
- `crates/sidequest-server/src/dispatch/mod.rs` — call `deplete_light_on_transition()` after successful room-graph move, emit OTEL `item.depleted` span + narration message

**Tests:** 510/510 passing (GREEN)
**Branch:** feat/19-5-consumable-item-depletion (pushed)

**Handoff:** To Reviewer

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): `InventoryItem` in sidequest-protocol does not include `uses_remaining` field. Affects `crates/sidequest-protocol/src/message.rs`. *Found by TEA during test design.*
- **Gap** (non-blocking): No `GameMessage` variant for item depletion events. Dev used inline Narration message. Affects protocol design. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): Used `GameMessage::Narration` for depletion message rather than adding a new protocol variant. Avoids client-side changes but means the UI can't distinguish depletion from regular narration. *Found by Dev during implementation.*

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Tests are GREEN not RED — pre-existing implementation**
  - Spec source: context-story-19-5.md, TDD workflow
  - Spec text: "RED phase — write failing tests"
  - Implementation: Tests pass because consume_use() and deplete_light_on_transition() were already implemented
  - Rationale: Writing tests for untested existing code provides regression safety
  - Severity: minor
  - Forward impact: none

### Dev (implementation)
- **Used Narration message instead of dedicated protocol variant**
  - Spec source: context-story-19-5.md, AC-4
  - Spec text: "Fire GameMessage when a light source is exhausted"
  - Implementation: Emitted `GameMessage::Narration` with depletion text instead of a new `GameMessage::ItemDepleted` variant
  - Rationale: Adding a protocol variant requires client-side changes and breaks `#[serde(deny_unknown_fields)]` for existing clients. The narration approach delivers the information without protocol changes.
  - Severity: minor
  - Forward impact: UI cannot programmatically detect light exhaustion (e.g., for screen dimming effect). If needed, add protocol variant in a future story.