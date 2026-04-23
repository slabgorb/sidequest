---
story_id: "26-10"
jira_key: "none"
epic: "26"
workflow: "tdd"
---

# Story 26-10: Wire map cartography data through dispatch to UI

## Story Details

- **ID:** 26-10
- **Jira Key:** none (personal project)
- **Epic:** 26 — Wiring Audit Remediation
- **Workflow:** tdd (phased: setup → red → green → spec-check → verify → review → spec-reconcile → finish)
- **Points:** 5
- **Priority:** p1
- **Stack Parent:** none

## Workflow Tracking

**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-06T18:29:20Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-06T18:29:20Z | - | - |

## Delivery Findings

No upstream findings.

## Design Deviations

None yet.

## Implementation Context

### Story Goal

Wire the cartography system (maps, regions, explored locations, navigation metadata) from genre packs through the dispatch pipeline to the UI. The genre loader already reads `cartography.yaml` from each world, but this data is not currently being sent to clients in the MAP_UPDATE message.

### Current State

**Wiring Status:** Partial
- MAP_UPDATE message exists and is sent every turn (message.rs, dispatch/mod.rs)
- MapUpdatePayload structure exists with: `current_location`, `region`, `explored`, `fog_bounds`
- GenreLoader loads cartography config but it's not accessed during dispatch
- DispatchContext has `rooms` and `world_graph` fields but no cartography reference

**Protocol Status:** Complete
- GameMessage::MapUpdate is defined
- MapUpdatePayload is defined with `#[serde(deny_unknown_fields)]`
- No new message types needed (26-7 already completed)

**UI Status:** Unknown
- React component should consume MAP_UPDATE and render map overlay
- Need to verify Map component can handle cartography data structure

### Current Implementation Gap

The MAP_UPDATE message currently sends only:
- `current_location`: current room/location string
- `region`: same as current_location (error — should be region name)
- `explored`: vec of ExploredLocation (has name, coordinates)
- `fog_bounds`: None (not implemented)

**Missing:** Cartography metadata from genre pack:
- Region definitions (name, description, adjacent regions)
- Route definitions (from/to regions, travel cost, description)
- Navigation mode (region vs room_graph vs hierarchical)
- Room graph structure (for room_graph mode)
- Starting region for UI map initialization

### Implementation Approach

1. **RED phase:** Write acceptance tests verifying MAP_UPDATE contains:
   - Navigation mode from cartography config
   - All regions from cartography.regions
   - All routes from cartography.routes
   - Current region (not just location)
   - Explored locations with correct region association

2. **GREEN phase:**
   - Add GenreLoader call in dispatch to load CartographyConfig
   - Extend MapUpdatePayload to include cartography metadata OR create separate CARTOGRAPHY_DATA message
   - Emit MAP_UPDATE on session init and on location changes
   - Validate room/location mapping against cartography

3. **Spec-check:** Verify no protocol breaking changes (new fields should be optional if added to MapUpdatePayload)

4. **Verify/Review:** Ensure wiring is complete end-to-end (dispatch → UI consumption)

### Files to Touch

- `sidequest-api/crates/sidequest-protocol/src/message.rs` — possibly extend MapUpdatePayload or add CARTOGRAPHY_DATA variant
- `sidequest-api/crates/sidequest-server/src/dispatch/mod.rs` — wire cartography into MAP_UPDATE generation
- `sidequest-api/crates/sidequest-server/src/dispatch/connect.rs` — send initial cartography on session connect
- `sidequest-ui/src/...` — verify MapOverlay or Map component consumes cartography data (discovery phase)

### Risks / Questions

- Should cartography be in MAP_UPDATE or separate CARTOGRAPHY_DATA message? MAP_UPDATE is large but cartography is map-specific, so probably same message.
- Do we need to distinguish between "current_location" (a room) and "current_region" (region) in the payload? Protocol may need adjustment.
- Is ExploredLocation the right structure for cartography, or do we need a new CartographyRegion type?
