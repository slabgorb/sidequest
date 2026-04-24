---
id: 61
title: "Lore Module Decomposition — Split lore.rs by Responsibility"
status: accepted
date: 2026-04-04
deciders: [Keith]
supersedes: []
superseded-by: null
related: [3, 59]
tags: [codebase-decomposition]
implementation-status: live
implementation-pointer: null
---

# ADR-061: Lore Module Decomposition — Split lore.rs by Responsibility

> **Status amendment (2026-04-23):** Executed during the Python port (ADR-082).
> Realized as sibling modules `lore_store.py` / `lore_seeding.py` /
> `lore_embedding.py` under `sidequest-server/sidequest/game/` rather than
> a subdirectory. See the Post-port mapping section at the end.

## Context

`sidequest-game/src/lore.rs` is the largest file in the Rust codebase at 2,901 lines.
It contains 6 types, 3 impl blocks, and 31 public functions spanning five distinct
responsibilities:

1. **Core types and storage** — `LoreStore`, `LoreFragment`, `LoreCategory`, `LoreSource`
   with CRUD operations, embedding storage, and similarity search
2. **Seeding** — `seed_lore_from_genre_pack()`, `seed_lore_from_char_creation()` —
   populate the store from genre pack data at session start
3. **Prompt assembly** — `select_lore_for_prompt()`, `format_lore_context()` — budget-aware
   selection and XML formatting for narrator prompt injection
4. **Accumulation** — `accumulate_lore()`, `accumulate_lore_batch()` — extract and ingest
   lore from narrator responses turn-by-turn
5. **Language/name knowledge** — `record_language_knowledge()`, `record_name_knowledge()`,
   `query_language_knowledge()` — conlang integration for NPC naming consistency

Plus ~1,200 lines of tests covering all five areas.

## Decision

**Split `lore.rs` into a `lore/` directory with responsibility-grouped submodules.**

### Module Structure

```
sidequest-game/src/lore/
├── mod.rs              # Re-exports public API
├── types.rs            # LoreStore, LoreFragment, LoreCategory, LoreSource,
│                       #   cosine_similarity() — core types and storage operations
├── seeding.rs          # seed_lore_from_genre_pack(), seed_lore_from_char_creation()
├── prompt.rs           # select_lore_for_prompt(), format_lore_context(),
│                       #   FragmentSummary, LoreRetrievalSummary,
│                       #   summarize_lore_retrieval()
├── accumulate.rs       # accumulate_lore(), accumulate_lore_batch()
└── language.rs         # record_language_knowledge(), record_name_knowledge(),
                        #   query_language_knowledge()
```

### Test Organization

Tests move with their module. Each submodule gets a `#[cfg(test)] mod tests` block
with the tests relevant to that responsibility. The current monolithic test block
(~1,200 lines) splits accordingly.

### Why This Split

The five responsibilities have distinct dependency profiles:
- `types.rs` depends on nothing outside `std` + `serde`
- `seeding.rs` depends on `sidequest-genre` types
- `prompt.rs` depends on token budgeting logic
- `accumulate.rs` depends on parsing/extraction
- `language.rs` depends on conlang corpus types

These are natural seams — minimal cross-references between responsibilities.

## Alternatives Considered

### Split only tests into a separate file
Would reduce the visual size but not the coupling. The 31 public functions in one
namespace is the real problem. Rejected.

### Extract lore into its own crate
Tempting given the size, but `LoreStore` is tightly coupled to `GameState` mutation.
A crate boundary would require passing `GameState` across crate lines or introducing
a trait abstraction that doesn't earn its keep yet. Revisit if lore grows further
or needs to be shared with another consumer. Rejected for now.

## Consequences

- **Positive:** Each module is 400-600 lines. Clear ownership — adding a new lore
  source type? `seeding.rs`. Changing prompt formatting? `prompt.rs`.
- **Positive:** `language.rs` makes the conlang-lore integration explicit and
  discoverable rather than buried at line 649 of a 2,900-line file.
- **Negative:** One-time migration. Re-exports in `mod.rs` preserve the public API.
- **Risk:** `accumulate.rs` may need access to `LoreStore` internals. If so, keep
  accumulation methods as `impl LoreStore` in `accumulate.rs` (Rust allows impl
  blocks in any module within the same crate).

## Post-port mapping (ADR-082)

Post-port, lore responsibilities are split across sibling modules in
`sidequest-server/sidequest/game/`:

- `lore_store.py` — `LoreStore`, fragment lookup, injection budgeting
- `lore_seeding.py` — genre pack seeding
- `lore_embedding.py` — cross-process embedding bridge to the daemon (ADR-048)

The Rust `sidequest-game/src/lore.rs` single-file origin is historical. The
"impl blocks in any module" accommodation in the original ADR is unnecessary in
Python — accumulator methods live on `LoreStore` in `lore_store.py`.
