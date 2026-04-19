---
story_id: "11-5"
jira_key: "none"
epic: "11"
workflow: "tdd"
---
# Story 11-5: Lore accumulation

## Story Details
- **ID:** 11-5
- **Title:** Lore accumulation — world state agent writes new lore fragments from game events
- **Points:** 3
- **Priority:** P1
- **Workflow:** tdd
- **Status:** in-progress
- **Stack Parent:** none (depends on 11-1, 11-2, 11-3, 11-4 — all merged)
- **Repository:** sidequest-api
- **Branch:** feat/11-5-lore-accumulation

## Story Description

The world state agent should be able to create new lore fragments dynamically from game events.
This enables the game to accumulate and evolve its own narrative facts as play progresses.

### Requirements
- Allow the world state agent to create new `LoreFragment`s from game event descriptions
- New fragments should have `source: LoreSource::GameEvent` and `turn_created` set to the current turn number
- Provide a helper function to create lore fragments from an event description with optional category inference
- Support categories being inferred from event context or explicitly provided
- Track when lore was added (turn number for timestamping)
- Integrate seamlessly with the existing `LoreStore.add()` method

### Target Module
`crates/sidequest-game/src/lore.rs` — extend the lore system to support runtime fragment creation.

## Workflow Tracking

**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-03-27

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-27 | - | - |

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

None yet.

## Context: Lore System Overview

The lore system is a three-layer architecture for world-building:

### 1. LoreFragment (Story 11-1) ✓
A single indexed piece of world knowledge with:
- `id`: unique identifier
- `category`: History, Geography, Faction, Character, Item, Event, Language, or Custom
- `content`: narrative text
- `token_estimate`: ~4 chars per token (for context budgeting)
- `source`: GenrePack, CharacterCreation, or **GameEvent** (new for 11-5)
- `turn_created`: optional turn number when added
- `metadata`: arbitrary key-value pairs

### 2. LoreStore (Story 11-2) ✓
In-memory indexed collection with:
- `add(fragment)`: insert a fragment, reject duplicates
- `query_by_category(category)`: retrieve all fragments in a category
- `query_by_keyword(keyword)`: full-text search
- `total_tokens()`: sum of all token estimates
- `len()`: fragment count

### 3. Lore Seeding (Story 11-3) ✓
Initialize the store from:
- Genre pack: history, geography, cosmology, factions
- Character creation: anchored character facts

### 4. Lore Injection (Story 11-4) ✓
Select and format relevant fragments for agent prompts based on:
- Contextual relevance (category match, keyword match)
- Token budget constraints

## Implementation Plan

### Phase 1: Test Suite (TDD)
Write tests in `crates/sidequest-game/src/lore.rs#[cfg(test)]` for:

1. **Fragment Creation from Event Description**
   - Create a fragment with event source and turn number
   - Verify id, category, content, source, turn_created are set correctly
   - Test with and without explicit category

2. **Category Inference (Optional)**
   - If event description contains keywords (e.g., "defeated", "discovered", "faction"), infer category
   - Fall back to `Event` category if no inference possible
   - Allow explicit override

3. **Turn Number Tracking**
   - Fragment must have turn_created set to current turn
   - Fragments from genre pack or char creation should have None

4. **Integration with LoreStore.add()**
   - Add a new event-sourced fragment to the store
   - Verify it appears in queries
   - Verify duplicate id detection still works

5. **Metadata Preservation**
   - Event source reference in metadata (e.g., "event_id", "turn_number")
   - Custom metadata from the event context

### Phase 2: Implementation
Add public functions to lore.rs:

```rust
/// Create a lore fragment from a game event.
pub fn create_lore_fragment_from_event(
    event_description: &str,
    category: Option<LoreCategory>,
    turn_number: u64,
    metadata: HashMap<String, String>,
) -> LoreFragment
```

And optionally:
```rust
/// Infer a lore category from event description keywords.
pub fn infer_category_from_event(description: &str) -> LoreCategory
```

## Testing Approach

TDD: Write failing tests first, then implement to make them pass.

Tests should cover:
- ✓ Fragment creation with explicit category
- ✓ Fragment creation with inferred category
- ✓ Turn number is correctly set
- ✓ Source is GameEvent
- ✓ Fragment can be added to store and queried
- ✓ Metadata is preserved
- ✓ Duplicate id still rejected
