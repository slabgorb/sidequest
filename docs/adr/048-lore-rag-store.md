---
id: 48
title: "Lore RAG Store with Cross-Process Embedding"
status: accepted
date: 2026-04-01
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [media-audio]
implementation-status: live
implementation-pointer: null
---

# ADR-048: Lore RAG Store with Cross-Process Embedding

> Retrospective — documents a decision already implemented in the codebase.

## Context
As a session progresses, the narrator extracts lore fragments from its own narration — named locations, faction details, character backstory, established world facts. These need to be retrievable at prompt-construction time to prevent continuity drift. A simple append-to-context strategy doesn't scale: after a long session, naively injecting all accumulated lore would exhaust the context budget.

The embedding model problem compounds the design: Rust has no mature sentence-transformers equivalent. The Python daemon already runs for image/audio generation. The embedding workload belongs there.

## Decision
`LoreStore` (in `sidequest-game`) maintains a dictionary of `LoreFragment` records indexed by category and keywords. Fragments are created in Rust from narrator-extracted structured output. Their text is sent to the Python daemon's `EmbedWorker`, which runs `all-MiniLM-L6-v2` via sentence-transformers and returns a 384-dimensional vector. The vector is attached to the fragment via `set_embedding()` and stored in-process.

At prompt construction time, `LoreStore` supports two retrieval paths:
- `query_by_similarity(query_embedding, k)` — cosine distance, returns top-k fragments
- `query_by_keyword(term)` — substring match across fragment text and tags

Both paths feed into a token-budget-aware selector that greedily fills an available token budget before returning the final fragment set for prompt injection.

```rust
// sidequest-game/src/lore.rs
pub struct LoreFragment {
    pub id: Uuid,
    pub category: LoreCategory,
    pub text: String,
    pub keywords: Vec<String>,
    pub embedding: Option<Vec<f32>>,   // 384-dim, set async after daemon call
    pub token_cost: usize,
}

impl LoreStore {
    pub fn query_by_similarity(&self, query: &[f32], k: usize) -> Vec<&LoreFragment> { ... }
    pub fn select_within_budget(&self, candidates: Vec<&LoreFragment>, budget: usize) -> Vec<&LoreFragment> { ... }
}
```

The embedding pipeline is async: fragment creation is synchronous, embedding attachment is fire-and-forget with the vector written back when the daemon responds. Fragments without embeddings fall back to keyword-only retrieval in the interim.

## Alternatives Considered

**External vector database (Qdrant, Pinecone)** — rejected: operational overhead for a single-session, single-process game engine. A network round-trip to a separate process on every lore query adds latency without benefit at this scale.

**Keyword-only retrieval** — rejected: misses semantic relationships. "The Ember Throne" and "the seat of the fire king" are not keyword-adjacent but are semantically equivalent. Keyword-only retrieval forces exact terminology consistency on the narrator.

**LLM-based retrieval** — rejected: latency and cost. A Claude call to select relevant lore before every narration call doubles the round-trip and adds token cost, turning a retrieval problem into an inference problem.

**Embedding in Rust (candle/ort)** — rejected at this stage. Library maturity is lower than sentence-transformers, and the daemon already runs Python for media generation. Consolidating embedding there avoids introducing a second ML runtime.

## Consequences

**Positive:**
- Context window budget is managed explicitly — lore injection scales with session length without blowing the prompt.
- Semantic retrieval catches continuity references that keyword search would miss.
- Embedding model lives alongside other ML workloads in the daemon; no new runtime.

**Negative:**
- Async embedding introduces a window where new fragments are keyword-searchable but not similarity-searchable. During rapid narration sequences this could cause missed recalls.
- Cross-process embedding adds daemon dependency to the lore pipeline — if the daemon is slow or restarting, embedding attachment stalls.
- 384-dim float vectors per fragment have non-trivial memory cost at long session durations. No eviction policy exists yet.
