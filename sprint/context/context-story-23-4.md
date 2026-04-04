---
type: story
id: "23-4"
epic: "23"
title: "LoreFilter — graph-distance + intent-based context retrieval for Valley zone"
---

# Story 23-4: LoreFilter

## What

Build a `LoreFilter` struct in sidequest-agents that determines which lore sections to inject into the narrator prompt per turn, replacing the current "dump everything" approach.

## Why

The narrator prompt currently dumps all world lore into the Valley zone every turn. Most is irrelevant to the current scene — wasting tokens, diluting attention, and scaling badly as content grows. This story is Layer 2+3 of the three-layer RAG strategy (docs/narrator-prompt-rag-strategy.md).

## Dependencies (all complete)

- **23-1:** Reworked prompt template with attention zones
- **23-2:** Tiered lore summaries (summary field on factions/cultures/locations)
- **23-3:** Universal room graph cartography (hierarchical world_graph + sub_graphs)

## Technical Approach

### LoreFilter struct

Lives in `sidequest-agents` — new module `lore_filter.rs` or integrated into orchestrator.

**Input signals:**
1. **Graph distance** (primary) — from current_node via cartography graph
2. **Intent classification** — Combat/Dialogue/Travel/Trade/Backstory
3. **NPC presence** — NPCs in scene pull their faction/culture
4. **Arc proximity** — arcs near next beat get full detail

**Output:** `Vec<LoreSelection>` — entity + detail level (Full, Summary, NameOnly)

### Detail levels by graph distance

| Distance | Detail Level |
|----------|-------------|
| 0 hops (current) | Full description + NPCs + items + state |
| 1 hop (adjacent) | Full description + edge properties |
| Same sub-graph | Available on demand |
| 2+ hops | Summary or name-only |

### Integration point

`orchestrator.rs:build_narrator_prompt()` (L254-559) currently registers all lore sections unconditionally. Gate Valley section registration through LoreFilter.select_lore().

### OTEL

Add `lore_filter` span logging included/excluded decisions per turn for GM panel observability.

## Key Files

| File | Role |
|------|------|
| `crates/sidequest-agents/src/orchestrator.rs` | Prompt assembly — call filter here |
| `crates/sidequest-agents/src/prompt_framework/types.rs` | PromptSection, AttentionZone |
| `crates/sidequest-game/src/state.rs` | Game state with current_node, NPCs, intent |
| `docs/narrator-prompt-rag-strategy.md` | Full RAG strategy spec |
| `docs/universal-room-graph-cartography.md` | Graph format spec |

## Acceptance Criteria

- LoreFilter struct with full unit test coverage
- build_narrator_prompt() calls filter instead of dumping all lore
- Graph distance calculation verified with Zork-style traversal
- Intent-to-lore mapping for Combat/Dialogue/Travel/Trade/Backstory
- NPC-driven faction/culture enrichment
- OTEL span logs included/excluded decisions
- Name-only closed-world assertions always present
- Full workspace build passes
- Integration test confirms filter wiring end-to-end
