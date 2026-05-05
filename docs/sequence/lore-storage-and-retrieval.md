# Lore Storage and Retrieval

> **Last updated:** 2026-05-05 (post-port; ADR-082)
>
> Knowledge indexing with category/keyword/semantic search, budget-aware prompt injection,
> and background embedding via the Python daemon. Two parallel systems feed the narrator:
> LoreStore (world knowledge) and KnownFacts (character knowledge).
>
> Module paths reference `sidequest-server/sidequest/` (Python). The pre-port
> Rust crate paths in earlier revisions of this document have been retired —
> see `docs/adr/082-port-api-rust-to-python.md`.

## System Overview

```mermaid
flowchart TD
    subgraph Sources
        GP[Genre Pack YAML<br/>history, geography,<br/>factions, cosmology]
        CC[Character Creation<br/>scene choices]
        NR[Narrator Output<br/>footnotes + game events]
    end

    subgraph Storage
        LS[LoreStore<br/>HashMap by fragment ID]
        DB[(SQLite<br/>persistent)]
        KF[KnownFacts<br/>per-character array]
    end

    subgraph Retrieval
        SEM[Semantic Search<br/>cosine similarity]
        KW[Keyword Search<br/>substring match]
        CAT[Category Search<br/>priority ordering]
        GD[Graph-Distance Filter<br/>LoreFilter + WorldGraph]
    end

    subgraph Injection
        PROMPT[Narrator Prompt<br/>Valley zone]
    end

    GP -->|seed_lore_from_genre_pack| LS
    CC -->|seed_lore_from_char_creation| LS
    NR -->|accumulate_lore| LS
    NR -->|footnotes → DiscoveredFact| KF
    LS -->|persist| DB
    LS --> SEM & KW & CAT
    KF --> PROMPT
    SEM & KW & CAT --> PROMPT
    GD --> PROMPT
```

## Session Initialization

```mermaid
sequenceDiagram
    participant S as Server (server/app.py)
    participant LS as LoreStore (asyncio.Lock-guarded)
    participant EW as Embed Worker (background asyncio.Task)
    participant C as handlers/connect.py

    S->>LS: LoreStore()
    S->>S: create asyncio.Queue (lore_embed_queue)
    S->>EW: asyncio.create_task(embed_worker(lore_store, queue))
    Note over EW: Background task starts<br/>Initial sweep: embed any pending fragments

    C->>LS: seed_lore_from_genre_pack(&mut store, genre_pack)
    Note over LS: Creates fragments:<br/>lore_genre_history<br/>lore_genre_geography<br/>lore_genre_cosmology<br/>lore_genre_faction_{slug}
    C->>LS: seed_lore_from_char_creation(&mut store, scenes)
    Note over LS: Creates fragments:<br/>lore_char_creation_{scene}_{choice}
```

## Turn-by-Turn: Accumulation and Embedding

```mermaid
sequenceDiagram
    participant D as Dispatch Loop
    participant LS as LoreStore
    participant DB as SQLite
    participant TX as asyncio.Queue
    participant EW as Embed Worker
    participant DM as Daemon (embed)

    Note over D: Narrator returns narration + footnotes

    D->>LS: accumulate_lore(text, category, turn, metadata)
    Note over LS: id = "evt-{turn}-{hash:016x}"<br/>token_estimate = len/4<br/>source = GameEvent
    LS-->>D: fragment_id

    D->>DB: append_lore_fragment(fragment)
    D->>D: OTEL: lore.fragment_accumulated

    D->>TX: send(EmbedRequest { fragment_id, text })
    Note over TX: Non-blocking fire-and-forget

    Note over EW: Background — decoupled from dispatch

    EW->>TX: await queue.get()
    EW->>EW: Check circuit breaker state

    alt Circuit closed
        EW->>DM: client.embed(EmbedParams { text })
        Note over DM: Unix socket JSON-RPC<br/>/tmp/sidequest-renderer.sock<br/>~10s call held OUTSIDE lock
        DM-->>EW: EmbedResult { embedding, model, latency_ms }
        EW->>LS: set_embedding(id, embedding)
        EW->>EW: OTEL: lore.embedding_generated
    else Circuit open (3+ failures)
        EW->>LS: mark_embedding_pending(id)
        EW->>EW: OTEL: lore.embedding_circuit_open
        Note over EW: Wait 30s → half-open probe
    end
```

## Prompt Injection: Budget-Aware Selection

```mermaid
sequenceDiagram
    participant PR as agents/prompt_framework
    participant LS as LoreStore
    participant DM as Daemon (embed)
    participant LF as LoreFilter
    participant WG as WorldGraph

    Note over PR: build_prompt_context() — Valley zone

    PR->>PR: Determine priority categories<br/>in_combat → [Event, Character]<br/>in_chase → [Geography]<br/>default → [Geography, Faction]

    rect rgb(240, 248, 255)
        Note over PR,LS: Phase 1 — Quick check (with lock)
        PR->>LS: fragments_with_embeddings_count()
        LS-->>PR: count (determines if semantic search viable)
    end

    rect rgb(255, 248, 240)
        Note over PR,DM: Phase 2 — Query embedding (NO lock held)
        PR->>DM: client.embed(EmbedParams { text: current_location })
        alt Daemon available
            DM-->>PR: EmbedResult { embedding: Vec<f32> }
        else Daemon unavailable
            DM-->>PR: error
            PR->>PR: OTEL: lore.query_embedding_failed<br/>fallback to keyword/category
        end
    end

    rect rgb(240, 255, 240)
        Note over PR,LS: Phase 3 — Select fragments (with lock)
        PR->>LS: select_lore_for_prompt(budget=500, priority, query_embedding)
        Note over LS: Ranking pipeline:<br/>1. Semantic similarity (if embedding)<br/>2. Category priority<br/>3. Recency (newer events first)<br/>Greedy select until budget exhausted
        LS-->>PR: Vec<&LoreFragment>

        PR->>PR: format_lore_context(selected)<br/>→ markdown grouped by category
        PR->>PR: summarize_lore_retrieval()<br/>→ OTEL: lore.LoreRetrieval
    end

    rect rgb(248, 240, 255)
        Note over LF,WG: Parallel — Graph-distance filtering
        PR->>LF: select_lore(current_node, intent, npcs, arcs)
        LF->>WG: graph_distance(from, to) for each node
        Note over LF: Layer 1: distance → detail level<br/>  0-1 hops → Full<br/>  2 hops → Summary<br/>  3+ hops → NameOnly<br/>Layer 2: NPC presence enrichment<br/>Layer 3: Intent-based boost
        LF-->>PR: Vec<LoreSelection>
        PR->>PR: format_prompt_section(selections)
    end

    PR->>PR: Append lore + filter + known_facts to state_summary
```

## KnownFact Injection

```mermaid
flowchart TD
    NR[Narrator output] -->|extract_footnotes| FN[Footnotes]
    FN --> DF[DiscoveredFact<br/>character_name + KnownFact]
    DF --> KFA[character.known_facts<br/>monotonic append, no decay]

    KFA -->|prompt.rs| SELECT[Take most recent 20]
    SELECT --> FMT["Format per fact:<br/>[Category] content"]
    FMT --> INJECT["Inject under<br/>[CHARACTER KNOWLEDGE]<br/>section in prompt"]
```

**KnownFact fields:**
- `content` — fact in genre voice
- `learned_turn` — when discovered
- `source` — Observation, Dialogue, Discovery, Backstory
- `confidence` — Certain, Suspected, Rumored
- `category` — Lore, Place, Person, Quest, Ability

## LoreFilter Detail Levels

```mermaid
flowchart LR
    subgraph "Graph Distance → Detail"
        D0["0-1 hops<br/>FULL"] --- D2["2 hops<br/>SUMMARY<br/>~10 tokens"]
        D2 --- D3["3+ hops<br/>NAME ONLY<br/>+ 'do not invent'"]
    end
```

The NameOnly tier includes a closed-world assertion: "do not invent details about locations you only know by name." This prevents narrator hallucination about distant locations.

**Enrichment layers** override distance-based filtering:
- **NPC presence:** NPCs in the current scene pull their faction/culture to Full regardless of distance
- **Intent-based:** Combat boosts faction lore, Dialogue boosts culture+faction, Exploration boosts location

## LoreFragment Data Model

```
LoreFragment (pydantic v2 model)
├── id: str (deterministic: "evt-{turn}-{hash}" or "lore_genre_{section}")
├── category: LoreCategory (StrEnum)
│   └── History | Geography | Faction | Character | Item | Event | Language | Custom
├── content: str (narrative text)
├── token_estimate: int (~chars/4)
├── source: LoreSource
│   └── GenrePack | CharacterCreation | GameEvent
├── turn_created: int | None
├── metadata: dict[str, str]
├── embedding: list[float] | None  (from daemon)
└── embedding_pending: bool (retry flag)
```

## Key Files

| File | Purpose |
|------|---------|
| `sidequest-server/sidequest/game/lore_store.py` | `LoreStore`, query methods, embedding management |
| `sidequest-server/sidequest/game/lore_seeding.py` | `seed_lore_from_genre_pack`, `seed_lore_from_char_creation` |
| `sidequest-server/sidequest/game/lore_embedding.py` | Cross-process embedding via daemon (ADR-048); cosine similarity |
| `sidequest-server/sidequest/game/character.py` | `KnownFact`, `DiscoveredFact`, `FactCategory` |
| `sidequest-server/sidequest/agents/prompt_framework/` (`core.py`, `soul.py`, `types.py`) | `build_prompt_context`, lore injection pipeline |
| `sidequest-server/sidequest/server/dispatch/lore_embed.py` | Per-turn embedding fan-out / accumulate-and-persist |
| `sidequest-server/sidequest/daemon_client/` | Daemon embedding RPC client (Unix socket, ADR-035) |
| `sidequest-server/sidequest/telemetry/spans/lore.py` + `rag.py` | OTEL span definitions (lore + RAG) |

## OTEL Events

| Event | Type | When |
|-------|------|------|
| `lore.fragment_accumulated` | StateTransition | Fragment added (category, turn, tokens) |
| `lore.fragment_persisted` | StateTransition | Saved to SQLite |
| `lore.embedding_generated` | StateTransition | Vector attached (latency_ms, model) |
| `lore.embedding_pending` | ValidationWarning | Marked for retry (daemon failure) |
| `lore.embedding_circuit_open` | ValidationWarning | 3+ consecutive failures |
| `lore.semantic_retrieval` | StateTransition | Fragment selection (fallback, count) |
| `lore.LoreRetrieval` | Custom | Full budget breakdown (selected, rejected, tokens) |
| `lore.query_embedding_failed` | ValidationWarning | Daemon unreachable for query |
| `rag.known_facts_injected` | Summary | Character knowledge count |
| `rag.lore_injected_to_prompt` | Traced | Fragment count, tokens, categories |
