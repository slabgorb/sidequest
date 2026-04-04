# Story 23-2: Tiered Lore Summaries — Context for TEA Phase

## Problem Statement

The narrator system prompt dumps all world lore (factions, cultures, locations, history, geography, arcs, SFX) into every turn's Valley zone. Most is irrelevant to the current scene, wasting tokens and diluting attention. This scales badly as content grows.

**Why summaries are the safety net:** The three-layer retrieval strategy (docs/narrator-prompt-rag-strategy.md) uses:
1. Always-present names + summaries (cheap safety)
2. Graph-distance-based retrieval (story 23-3, full descriptions for nearby locations)
3. Signal-based enrichment (story 23-4, pull lore for relevant NPCs/factions)

If Layer 2 or Layer 3 miss-retrieves, summaries ensure the narrator has *something* about an entity (not zero context).

## Acceptance Criteria (from session file)

1. **YAML Schema Extension**
   - Add `summary:` field to faction, culture, location definitions in sidequest-content
   - Summary format: one line, ~10 tokens (15-20 characters)
   - Summaries are required (not optional) for filtering to be safe
   - Write summaries for low_fantasy as pilot (all factions, cultures, locations)

2. **Loader Implementation**
   - Update sidequest-genre loader to parse `summary:` field for Faction, Culture, Location
   - Make summaries accessible via public API (accessor methods)
   - Add unit tests for summary parsing with YAML fixture

3. **Protocol Alignment**
   - Check if sidequest-protocol types need updates to expose summaries (likely not — summaries are for narrator context, not player display)

4. **Integration & Validation**
   - Build passes, clippy clean, all tests green
   - Low_fantasy loads without errors
   - Orchestrator can access summaries via public API (no wiring required yet)

## Design Approach

### YAML Schema (low_fantasy pilot)

Add `summary:` field to each entity type. Example:

```yaml
factions:
  crown_remnant:
    name: Crown Remnant
    summary: "Descendants of the fallen kingdom seeking to restore order"
    description: |
      The Crown Remnant traces its lineage...
```

### Struct Changes (sidequest-genre)

1. Add `summary: String` field to Faction, Culture, Location structs
2. serde will auto-parse when YAML is loaded
3. Implement getter method (e.g., `pub fn summary(&self) -> &str`)
4. Omit `#[serde(default)]` so missing summaries cause deserialization errors (required fields)

### Tests

Unit test that loads a YAML fragment with summaries and verifies they parse correctly and are accessible.

## Dependency Graph

**No upstream dependencies.** 23-2 is independent.

**Enables:** Story 23-4 (LoreFilter) depends on 23-2 + 23-3.

## Key Files

| File | Role | Repo |
|------|------|------|
| `sidequest-content/genre_packs/low_fantasy/factions.yaml` | Faction YAML | content |
| `sidequest-content/genre_packs/low_fantasy/cultures.yaml` | Culture YAML | content |
| `sidequest-content/genre_packs/low_fantasy/locations.yaml` | Location YAML | content |
| `sidequest-api/crates/sidequest-genre/src/models/faction.rs` | Faction struct | api |
| `sidequest-api/crates/sidequest-genre/src/models/culture.rs` | Culture struct | api |
| `sidequest-api/crates/sidequest-genre/src/models/location.rs` | Location struct | api |
| `sidequest-api/crates/sidequest-genre/src/loaders/faction.rs` | Faction loader | api |
| `sidequest-api/crates/sidequest-genre/src/loaders/culture.rs` | Culture loader | api |
| `sidequest-api/crates/sidequest-genre/src/loaders/location.rs` | Location loader | api |

## Test Strategy

RED phase focus:

1. **Unit test: Faction summary parsing**
   - Load a YAML fixture with `summary:` field
   - Verify `faction.summary()` returns the expected value
   - Test that missing `summary:` causes deserialization error (required field)

2. **Unit test: Culture summary parsing**
   - Same pattern as faction

3. **Unit test: Location summary parsing**
   - Same pattern as faction

4. **Integration test: Low_fantasy genre pack loads**
   - Load the full low_fantasy pack
   - Verify no deserialization errors
   - Spot-check a few factions/cultures/locations have summaries set

## Technical Notes

- serde handles YAML→Rust deserialization automatically; adding a field and writing test fixture is all that's needed
- Summaries are internal (not exposed in game state payloads yet); protocol changes can be deferred
- No OTEL instrumentation needed for 23-2; story 23-4 adds the lore_filter span
- No UI rendering; summaries are for narrator context injection only

## Narrative Examples (for summary length calibration)

Good summary (~10 tokens, 15-20 chars):
- "Descendants of the fallen kingdom" (6 tokens)
- "Pragmatic traders united by profit" (6 tokens)
- "Isolated village at the mountain pass" (6 tokens)

Too long:
- "A coalition of merchants and traders who have banded together to expand their trade networks across the realm" (way over budget)

## Epic Context

Story 23-2 is part of Epic 23: Narrator Prompt Architecture. See docs/narrator-prompt-rag-strategy.md for the full strategy.

Stories 23-1 (done), 23-3 (parallel), and 23-4 (blocked on 23-2 + 23-3) are the core narrative RAG pipeline.
