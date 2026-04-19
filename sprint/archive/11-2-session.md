---
story_id: "11-2"
epic: "11"
epic_title: "Lore & Language — RAG Retrieval, Conlang Name Banks"
workflow: "tdd"
---
# Story 11-2: LoreStore — in-memory indexed collection with add, query by category, query by keyword

## Story Details
- **ID:** 11-2
- **Title:** LoreStore — in-memory indexed collection with add, query by category, query by keyword
- **Points:** 3
- **Priority:** p0
- **Epic:** 11 — Lore & Language
- **Workflow:** tdd
- **Stack Parent:** 11-1 (LoreFragment model, already merged to develop)

## Story Description

The narrator needs to retrieve world-building facts on demand. LoreStore is an in-memory
collection that holds LoreFragments and supports three main operations:

1. **add()** — Insert a new LoreFragment into the store
2. **by_category()** — Return all fragments matching a LoreCategory (fixed or custom)
3. **by_keyword()** — Return all fragments whose content contains a substring (case-insensitive)

Additionally, the store tracks total token count across all fragments for budget management
(context-window allocation in downstream retrieval layers).

**Core responsibility:** Implement an efficient, queryable in-memory lore index that supports
category-based and keyword-based retrieval with token accounting.

## Workflow Tracking

**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-03-27T20:45:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-27T20:45:00Z | - | - |

## Implementation Context

### Core Store Structure

```rust
#[derive(Debug, Clone)]
pub struct LoreStore {
    fragments: HashMap<String, LoreFragment>,
    by_category: HashMap<LoreCategory, Vec<String>>,
    total_tokens: usize,
}
```

The store maintains:
- `fragments`: Primary storage indexed by fragment ID
- `by_category`: Secondary index mapping categories to fragment IDs (for fast category queries)
- `total_tokens`: Sum of all fragment token_estimates for budget tracking

### Public API

```rust
impl LoreStore {
    pub fn new() -> Self { /* ... */ }

    pub fn add(&mut self, fragment: LoreFragment) -> Result<(), LoreStoreError> { /* ... */ }

    pub fn by_category(&self, category: &LoreCategory) -> Vec<&LoreFragment> { /* ... */ }

    pub fn by_keyword(&self, keyword: &str) -> Vec<&LoreFragment> { /* ... */ }

    pub fn total_tokens(&self) -> usize { /* ... */ }

    pub fn fragment(&self, id: &str) -> Option<&LoreFragment> { /* ... */ }
}
```

### Error Handling

```rust
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LoreStoreError {
    DuplicateId(String),  // Fragment ID already in store
}
```

### Implementation Notes

- **Indexing:** Category index is maintained at insertion time (no lazy building)
- **Keyword matching:** Case-insensitive substring search on content field
- **Token tracking:** Updated incrementally on add() and clear()
- **Memory model:** Owns LoreFragments; no references or lifetimes
- **Cloning:** Implement Clone for state snapshots (required for game session saving)

### Target Files

- `crates/sidequest-game/src/lore.rs` — Extend existing module with LoreStore implementation

### Architecture Notes

- This is a simple in-memory store, not persistent (persistence is handled elsewhere)
- No async operations; all queries are synchronous
- No locking or concurrent access (game state is single-threaded)
- Foundation for downstream stories: 11-3 (seeding from genre packs), 11-4+ (retrieval and injection)

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Struct compiles | `LoreStore` with all required fields |
| add() method | Accepts LoreFragment, rejects duplicates by ID, updates category index and token total |
| by_category() | Returns all fragments in a category; works with fixed and custom categories; empty vec if no matches |
| by_keyword() | Returns all fragments containing keyword (case-insensitive); empty vec if no matches |
| token_total | Correctly sums all fragments; increments on add, decrements on remove |
| fragment_lookup | by_id() retrieves individual fragments efficiently |
| Clone impl | LoreStore can be cloned for state snapshots |
| Error handling | DuplicateId error raised when adding fragment with existing ID |
| Tests cover | Add/retrieve, category queries (fixed and custom), keyword queries (case-insensitive), token tracking |

## Delivery Findings

Depends on 11-1 (LoreFragment model) which is already merged to develop.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

None recorded yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->
