---
id: 4
title: "Lazy Genre Binding"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: [38, 82]
tags: [core-architecture]
implementation-status: live
implementation-pointer: null
---

# ADR-004: Lazy Genre Binding

## Implementation status (2026-05-02)

The decision is honored end-to-end in the live Python tree. Wire-protocol shape lives under ADR-038; this ADR captures only the binding-time behavior.

- **Wire payload:** `sidequest-server/sidequest/protocol/messages.py:180` — `SessionEventPayload` carries `event`, `genre`, `world` (plus other event-specific fields documented inline).
- **Connect handler / lazy load:** `sidequest-server/sidequest/handlers/connect.py:283` — `genre_pack = loader.load(row.genre_slug)`. Pack is loaded the first time a session binds; the server starts with no pack in memory.
- **Session field:** `sidequest-server/sidequest/server/session_handler.py:422` — sessions carry a `genre_pack: GenrePack` attribute populated on connect.
- **Handler docstring:** `session_handler.py:7-8` — "SESSION_EVENT{connect}: bind genre/world, load or create GameSnapshot, emit SESSION_EVENT{connected}". Behavior matches the ADR.

Drift watch — if any of the following happens, this ADR is wrong:
- Server-side process boots a fixed genre pack from environment or CLI flag and refuses connect-time selection.
- A code path bypasses `SessionEventPayload` and binds genre/world through some other channel.

The original 2026-03-25 decision is preserved below.

## Context
Genre pack is runtime context, not a construction dependency.

## Decision
Server starts genre-agnostic. Genre is selected by the client on connect via `SESSION_EVENT { event: "connect", genre, world }`. The connect handler loads the genre pack on first bind; subsequent reconnects to the same session reuse it.

### Flow
1. Server starts — no genre loaded
2. Client connects, sends genre + world selection
3. Server loads genre pack from `sidequest-content/genre_packs/{genre}/`
4. Game session begins with loaded pack

> **Historical context (port era).** The 2026-03-25 sketch used Rust + `Option<GenrePack>` to model the pre-connect "no pack loaded" state. The current Python implementation tracks the same state implicitly — the session object's `genre_pack` attribute is populated only after connect handling. The Rust example is preserved as a record of the original decision.

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
- Enables genre selection UI in the client — the connect screen can present any pack discovered under `sidequest-content/genre_packs/`.
- Save files are genre-scoped; cross-genre loading is undefined.
- Faster server startup (no pack loaded until a session binds).
