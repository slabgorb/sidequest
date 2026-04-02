# Narrator Prompt RAG Strategy

Research document from 2026-04-02 prompt template review session.

## Problem

The narrator system prompt dumps all world lore (factions, cultures, locations, history, geography, arcs, SFX) into every turn's Valley zone. Most is irrelevant to the current scene. This wastes tokens, dilutes attention, and scales badly as content grows.

## Current Architecture

The prompt composer (`sidequest-agents/src/prompt_framework/`) uses attention zones:
- **Primacy** — identity, agency rules
- **Early** — SOUL principles, trope beats, tone
- **Valley** — game state, world lore, tools, merchant context, SFX (the dump zone)
- **Late** — verbosity/vocabulary settings
- **Recency** — player action

`build_narrator_prompt()` in `orchestrator.rs:254-559` assembles sections into zones. The infrastructure for conditional section registration already exists — merchant context only injects for Exploration/Dialogue intents. The pattern just needs to be extended.

## Strategy: Three-Layer Retrieval

### Layer 1: Always Present (cheap safety net)

Every turn includes:
- World name + one-line summary
- Current location name
- Comma-separated lists of all faction, culture, and location *names* (closed-world assertion — prevents hallucinating new entities)
- One-line arc summaries
- Player character sheets (inventory, HP, abilities — mechanical truth, never RAG'd)

Cost: ~50-80 tokens. Prevents contradictions even when full lore isn't loaded.

### Layer 2: Graph-Based Retrieval (primary mechanism)

Epic 19 (stories 19-1, 19-2, 19-3) shipped a Zork-style cyclic room graph for cartography. The plan is to make this the **universal cartography format across all genre packs**, replacing flat location lists.

**Hierarchical graphs:**
- **World graph** (coarse): cities/regions as nodes, roads/paths as edges
- **Sub-graphs** (fine): zoom into a node to see its internal structure (districts, rooms, areas)

**Retrieval by graph distance:**
| Distance | Detail Level | Example |
|----------|-------------|---------|
| 0 (current node) | Full description, NPCs, items, state | Always injected |
| 1 (adjacent nodes) | Full description + edge properties (danger, terrain) | Always injected |
| Same sub-graph | Available on demand | Narrator knows the neighborhood |
| Parent graph | Summary only | World-level context |
| 2+ hops | Name only | Exists but no detail |

**Edge properties as content:** Dangerous edges (danger > 0) generate travel scenes — encounters, weather, obstacles. Safe edges (danger = 0) are fast travel. The graph encodes the "Cut the Dull Bits" rule mechanically.

**Key insight:** The graph *is* the retrieval index. No keyword matching, no intent heuristics — just graph distance. One hop = full detail. Two hops = summary. Three+ = name only.

### Layer 3: Signal-Based Enrichment (supplements graph retrieval)

For content not tied to geography (faction politics, arc progression, backstory), use existing engine signals:

**Intent → lore mapping:**
```
Combat    → factions of NPCs in combat + local threats
Dialogue  → culture + faction of speaking NPC
Travel    → destination node + edge properties (graph handles this)
Trade     → merchant faction + currency lore
Backstory → full player backstory (normally summary-only)
```

**NPC-driven retrieval:** NPCs present in scene pull their faction and culture full descriptions. Already tracked in NPC registry.

**Arc proximity:** Only inject full arc descriptions for arcs within ~10% of their next beat threshold, or arcs connected to current-scene NPCs/factions. Dormant arcs (0% progress, next beat at 20%) get summary-only treatment.

## Tiered Lore Summaries (Prerequisite)

Every faction, culture, location, and arc needs two representations in genre pack YAML:
- `summary:` — one line, ~10 tokens, always present
- Full description — existing content, injected only when relevant

This must be built **before** the filter, because a retrieval miss with tiered lore means the narrator has a summary (safe). A retrieval miss without tiered lore means the narrator has nothing (dangerous).

**Implementation:**
1. Add `summary:` field to faction/culture/location/arc YAML schemas in sidequest-content
2. Write summaries for low_fantasy as pilot
3. Update sidequest-genre loader to parse summaries
4. build_narrator_prompt() always injects summaries, conditionally injects full descriptions

## SFX List

The full SFX ID list (21 entries in low_fantasy) is currently dumped every turn. With the `play_sfx` sidecar tool (story 20-7), the tool's parser already validates SFX IDs against the genre library. The narrator may still need the list to know *what's available* — but it could be trimmed to context-relevant SFX (combat SFX during combat, ambient SFX during exploration) or moved to a tool the narrator can query.

## Unresolved: Item Tools

Stories 20-11, 20-12, 20-13 (newly created) must land before the prompt template's tool section can be finalized. `item_acquire`, `merchant_transact`, and `lore_mark` are not wired into the sidecar pipeline — items narrated but never mechanically acquired.

## Prompt Template Impact

The `<world-lore>` section in the prompt template uses this pattern:

```xml
<world-lore>
World: {{world_name}}
{{world_summary}}

Current location: {{current_node.name}}
{{current_node.description}}

Exits:
{{#each current_node.exits}}
- {{direction}}: {{destination.name}}{{#if danger}} ({{danger}}){{/if}}
{{/each}}

Cultures: Brevonne, Nordmark, Khorvath
Factions: Crown Remnant, Merchant Consortium, ...
Locations: solenne, nordmark_heights, ...

{{#if relevant_lore}}
<lore topic="{{topic}}">{{content}}</lore>
{{/if}}
</world-lore>
```

The `relevant_lore` array is populated by the LoreFilter (graph distance + signal enrichment). Transitionally, the engine can dump everything into `relevant_lore` until the filter is built.

## OTEL Observability

Add a `lore_filter` OTEL span logging what was included/excluded each turn. The GM panel shows: "Injected: Crown Remnant (full), Solenne (full). Summary-only: Khorvath, Nordmark Heights. Excluded: none." This is the lie detector for retrieval quality.

## Implementation Sequence

1. Tiered lore summaries in genre pack YAML (content + loader)
2. Universal room graph cartography across all genre packs (content + genre crate)
3. LoreFilter struct in sidequest-agents (consumes graph + intent + NPCs)
4. Gate Valley section registration through LoreFilter in build_narrator_prompt()
5. OTEL span for filter decisions
6. Regression tests: "this turn at this node should include X, exclude Y"
