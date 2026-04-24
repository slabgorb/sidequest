---
id: 4
title: "Lazy Genre Binding"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [core-architecture]
implementation-status: live
implementation-pointer: null
---

# ADR-004: Lazy Genre Binding

> Ported from sq-2. Language-agnostic pattern.

## Context
Genre pack is runtime context, not a construction dependency.

## Decision
Server starts genre-agnostic. Genre is selected by the client on connect via `SESSION_EVENT { event: "connect", genre, world }`. The Orchestrator lazy-initializes the genre pack on first game action.

### Flow
1. Server starts — no genre loaded
2. Client connects, sends genre + world selection
3. Server loads genre pack from `genre_packs/{genre}/`
4. Game session begins with loaded pack

### Rust Pattern
```rust
struct Session {
    genre_pack: Option<GenrePack>,  // None until connect
    // ...
}

impl Session {
    fn ensure_genre_loaded(&mut self, genre: &str, world: &str) -> Result<&GenrePack> {
        if self.genre_pack.is_none() {
            self.genre_pack = Some(GenrePackLoader::load(genre, world)?);
        }
        Ok(self.genre_pack.as_ref().unwrap())
    }
}
```

## Consequences
- Enables genre selection UI in the client
- `--genre` CLI flag becomes a default hint, not a hard requirement
- Save files are genre-scoped; cross-genre loading is undefined
- Faster server startup (no pack loaded until needed)
