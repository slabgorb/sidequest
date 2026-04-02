# Universal Room Graph Cartography

Research document from 2026-04-02 prompt template review session.

## Decision

All genre pack cartography should use the cyclic room graph system shipped in Epic 19 (stories 19-1, 19-2, 19-3). This replaces flat location lists as the canonical cartography format across all genre packs.

## Background

Epic 19 built a Zork-style cyclic graph for the Caverns & Claudes genre pack (dungeon crawl). The graph supports:
- Nodes (rooms/locations) with descriptions, NPCs, items, state
- Directed edges (exits) between nodes
- Edge properties (danger level, terrain, traversal cost)
- Room transition events (trope ticks fire on movement)

Currently only used by one genre pack. All other genre packs use flat location lists — just names, no topology, no adjacency.

## Architecture: Hierarchical Graphs

Two levels:

### World Graph (coarse)
Nodes are major locations: cities, regions, landmarks, zones.
Edges are paths between them with properties:
- **danger**: 0 (fast travel) to N (story-generating encounters)
- **terrain**: road, wilderness, water, underground
- **distance**: affects travel time / number of beats

A dangerous edge is a *story-generating edge*. The danger level determines whether travel is narrated ("you arrive") or becomes a scene (ambush, weather, obstacle). This mechanically encodes the Hitchcock rule: no complication, no scene.

### Sub-Graphs (fine)
Each world-graph node can expand into its own internal graph.
- Solenne (world node) → docks, market, temple district, baron's keep (sub-nodes)
- The Stump (world node) → single room (no sub-graph needed)

Not every node needs a sub-graph. A remote farmstead is one node. A major city has districts. A dungeon has rooms.

### Example: Low Fantasy (Pinwheel Coast)

```
World Graph:
  solenne ←→ ash_approach_farmlands ←→ nordmark_heights
     ↕              ↕
  the_clatter    the_stump ←→ khorvath_steppe
     ↕
  pinwheel_shallows ←→ grudge_straits
                          ↕
                    the_glass_waste

Sub-graph (solenne):
  river_docks ←→ merchant_quarter ←→ temple_hill
       ↕                                  ↕
  warehouse_row                     brevonne_keep
```

### Example: Neon Dystopia

```
World Graph:
  downtown_spire ←→ industrial_sector ←→ port_district
       ↕                   ↕
  undercity          abandoned_ring ←→ corporate_campus

Sub-graph (downtown_spire):
  street_level ←→ mid_tower ←→ penthouse_tier
       ↕
  maintenance_tunnels
```

### Example: Space Opera

```
World Graph:
  bridge ←→ crew_quarters ←→ engineering
    ↕            ↕
  hangar_bay  med_bay ←→ science_lab
    ↕
  cargo_hold ←→ brig
```

The same graph system describes a fantasy continent, a cyberpunk city, and a starship. The granularity adapts to the genre.

## Benefits

### 1. Solves RAG / Context Retrieval
The graph is the retrieval index. Current node + adjacent nodes = relevant context. No keyword matching, no intent heuristics. Graph distance determines detail level:
- 0 hops: full detail (always injected)
- 1 hop: full detail (exits/neighbors)
- Same sub-graph: available on demand
- Parent graph: summary only
- 2+ hops: name only

### 2. Mechanical Travel Decisions
Players choose paths, not destinations. "Do I take the safe road or the shortcut through bandit territory?" is a meaningful decision the flat list can't support.

### 3. Story-Generating Edges
Dangerous paths produce scenes. Edge danger + edge terrain + edge encounter tables = deterministic "something happens during travel" without the narrator improvising.

### 4. NPC Locality
NPCs exist *at* nodes. The innkeeper is at solenne/merchant_quarter, not just "in Solenne." This enables:
- "Who's here?" queries
- NPC movement between nodes (the villain's army advances through the graph)
- Encounter generation tied to location

### 5. Consistent Navigation
The narrator can't teleport the player across the map. Travel is graph traversal. This prevents the "you walk for three days and arrive" hand-wave that breaks world consistency.

## Migration Path

### Phase 1: Schema
Define the universal graph YAML schema in sidequest-content. Two sections per world:
- `world_graph:` — top-level nodes and edges
- `sub_graphs:` — keyed by parent node, internal topology

### Phase 2: Convert Low Fantasy (Pilot)
Convert Pinwheel Coast's flat location list into a hierarchical graph. Add sub-graphs for Solenne (the most-playtested location).

### Phase 3: Genre Loader
Update sidequest-genre crate to parse the graph schema. CartographyConfig already exists from Epic 19 — extend it to support the hierarchical model.

### Phase 4: Narrator Integration
Update build_narrator_prompt() to inject current node, exits, and adjacent node summaries instead of the flat location list. Wire into the LoreFilter for graph-distance-based retrieval.

### Phase 5: Remaining Genre Packs
Convert all other genre packs. Some (space_opera, neon_dystopia) may have single-level graphs. That's fine — a world graph with no sub-graphs is valid.

## Relationship to Other Work

- **RAG strategy** (narrator-prompt-rag-strategy.md): Graph-based retrieval is the primary mechanism
- **Epic 19** (Dungeon Crawl): Built the graph infrastructure, currently genre-specific
- **Epic 16** (Genre Mechanics): Confrontation system may use graph edges for chase mechanics
- **MAP_UPDATE protocol** (story 19-4, backlog): Sends discovered nodes to UI for automapper
