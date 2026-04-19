---
story_id: "11-6"
jira_key: "none"
epic: "11"
workflow: "tdd"
---
# Story 11-6: Semantic retrieval

## Story Details
- **ID:** 11-6
- **Title:** Semantic retrieval — optional embedding-based RAG for lore query
- **Points:** 5
- **Priority:** P2
- **Workflow:** tdd
- **Status:** in-progress
- **Stack Parent:** none (depends on 11-1, 11-2, 11-3, 11-4, 11-5 — all merged)
- **Repository:** sidequest-api
- **Branch:** feat/11-6-semantic-retrieval

## Story Description

Extend the lore system with optional embedding-based semantic retrieval using vector similarity search.
This enables RAG (Retrieval-Augmented Generation) over lore by embedding distance rather than just keyword/category matching.
Embeddings are optional — the system must degrade gracefully to keyword search if embeddings are unavailable.

### Requirements
- Add an optional `embedding: Option<Vec<f32>>` field to `LoreFragment`
- Implement a trait or function for computing cosine similarity between embedding vectors
- Add a `query_by_similarity(query_embedding: &[f32], top_k: usize) -> Vec<&LoreFragment>` method to `LoreStore`
- The method should rank fragments by embedding distance (cosine similarity)
- Ensure the system works without embeddings (graceful fallback to keyword search)
- Embedding computation itself is out of scope (external service) — this story defines the data model and retrieval interface only
- Consider using cosine similarity metric for vector comparison

### Target Module
`crates/sidequest-game/src/lore.rs` — extend the lore system with vector embedding support.

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
- `source`: GenrePack, CharacterCreation, or GameEvent
- `turn_created`: optional turn number when added
- `metadata`: arbitrary key-value pairs
- **`embedding`: optional vector for semantic search (new for 11-6)**

### 2. LoreStore (Story 11-2) ✓
In-memory indexed collection with:
- `add(fragment)`: insert a fragment, reject duplicates
- `query_by_category(category)`: retrieve all fragments in a category
- `query_by_keyword(keyword)`: full-text search
- **`query_by_similarity(query_embedding, top_k)`: rank fragments by embedding distance (new for 11-6)**

### 3. Lore Seeding (Story 11-3) ✓
Initialize the store from:
- Genre pack: history, geography, cosmology, factions
- Character creation: anchored character facts

### 4. Lore Injection (Story 11-4) ✓
Select and format relevant fragments for agent prompts based on:
- Contextual relevance (category match, keyword match)
- Token budget constraints

### 5. Lore Accumulation (Story 11-5) ✓
Create new lore fragments dynamically from game events.

## Implementation Plan

### Phase 1: Test Suite (TDD)
Write tests in `crates/sidequest-game/src/lore.rs#[cfg(test)]` for:

1. **Embedding Field on LoreFragment**
   - Create a fragment with an embedding vector
   - Create a fragment without embedding (None)
   - Verify getters work for both cases

2. **Cosine Similarity Function**
   - Compute cosine similarity between two vectors
   - Edge cases: zero vectors, unit vectors, orthogonal vectors
   - Verify result is in range [0.0, 1.0]

3. **Semantic Query (No Embeddings)**
   - Call `query_by_similarity` with query embedding
   - Should return empty or gracefully handle fragments without embeddings
   - Verify it does not crash when store has only non-embedded fragments

4. **Semantic Query (With Embeddings)**
   - Add multiple fragments with embeddings to store
   - Query with a test embedding
   - Verify results are ranked by cosine similarity (highest first)
   - Verify `top_k` parameter limits result count

5. **Graceful Fallback**
   - Mix embedded and non-embedded fragments in store
   - Query by similarity should skip non-embedded or filter them out
   - Document the expected behavior (e.g., only embedded fragments ranked)

6. **Embedding Optional Field Serialization**
   - Verify serde correctly handles Option<Vec<f32>>
   - Test JSON round-trip with and without embedding

### Phase 2: Implementation
Add to lore.rs:

1. **Extend LoreFragment struct:**
   ```rust
   pub struct LoreFragment {
       // ... existing fields ...
       embedding: Option<Vec<f32>>,
   }
   ```

2. **Add getter:**
   ```rust
   pub fn embedding(&self) -> Option<&[f32]> {
       self.embedding.as_deref()
   }
   ```

3. **Add helper function for cosine similarity:**
   ```rust
   /// Compute cosine similarity between two vectors.
   /// Returns a value in [0.0, 1.0] where 1.0 is identical.
   pub fn cosine_similarity(a: &[f32], b: &[f32]) -> f32
   ```

4. **Add semantic query to LoreStore:**
   ```rust
   /// Query fragments by embedding similarity.
   /// Returns up to `top_k` fragments ranked by cosine similarity (highest first).
   /// Fragments without embeddings are skipped.
   pub fn query_by_similarity(&self, query_embedding: &[f32], top_k: usize) -> Vec<&LoreFragment>
   ```

5. **Update LoreFragment::new() or add a builder** to accept embedding.

## Testing Approach

TDD: Write failing tests first, then implement to make them pass.

Tests should cover:
- ✓ Fragment creation with embedding vector
- ✓ Fragment creation without embedding (Option::None)
- ✓ Cosine similarity computation (exact values)
- ✓ Semantic query returns top-k results by similarity
- ✓ Fragments without embeddings are handled gracefully
- ✓ Embedding is correctly serialized/deserialized
- ✓ Query with zero results returns empty vec

## Notes

- **Embedding computation out of scope:** This story defines the data model and query interface. Actual embedding computation (e.g., from an external API) is handled elsewhere.
- **Cosine similarity metric:** Standard for semantic search. Formula: `(a · b) / (||a|| * ||b||)`.
- **Graceful degradation:** The system must never break if embeddings are absent. Queries on non-embedded fragments should return empty or skip those fragments.
