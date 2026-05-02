---
id: 5
title: "Background-First Pipeline"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: [76, 82]
tags: [core-architecture]
implementation-status: live
implementation-pointer: null
---

# ADR-005: Background-First Pipeline

## Implementation status (2026-05-02)

The decision is honored — only narrator text is on the critical path; everything else is spawned. The spawn primitive is `asyncio.create_task` (Python equivalent of `tokio::spawn`); confirmed live at:

- `sidequest-server/sidequest/server/dispatch/lore_embed.py:154` — embedding worker
- `sidequest-server/sidequest/server/websocket.py:65` — writer task
- `sidequest-server/sidequest/server/websocket_session_handler.py:3274` — per-session async work

Three items from the original 2026-03-25 lists are dead and have been removed below:

- **Voice digest summarization** (critical path) and **Voice synthesis** (background) — TTS was fully removed; Kokoro is gone; voice frames no longer exist. See ADR-076 (Narration Protocol Collapse Post-TTS).
- **Speculative pre-generation** (background) — ADR-044 was marked `historical` in the 2026-05-02 hygiene sweep; the speculative pipeline never ported back to Python.

The `--sync-pipeline` debug flag mentioned in the original Consequences was a Rust-era ergonomic and is also gone (grep returns zero hits).

Drift watch — if any of the following happens, this ADR is wrong:
- A background task failure is allowed to propagate up and crash a session.
- An item moves from background to critical path (player blocks waiting on media).

## Context
Player-perceived latency is dominated by the narrator agent response. All other work (rendering, audio, world state patching) can happen in the background.

## Decision
Only the text response is on the critical path. Everything else is spawned as a background async task.

### Critical Path (awaited)
- Intent classification (LLM router)
- Primary agent call (narrator)

### Background (spawned)
- Image rendering (via daemon)
- Audio cue selection
- World state patching

### Error Handling
Background task failures are logged as warnings, never propagated as errors. The game continues with degraded media rather than crashing.

> **Historical context (port era).** The original 2026-03-25 sketch used `tokio::spawn` and `tracing::warn!`; the live implementation uses `asyncio.create_task` and the standard logging facade. The Rust example is preserved as a record of the original decision.

```rust
// Critical path — awaited
let response = agent.prompt(&player_action).await?;
ws_send(&response).await?;

// Background — spawned, never blocks the player
tokio::spawn(async move {
    if let Err(e) = render_scene(&response).await {
        tracing::warn!("Background render failed: {e}");
    }
});
tokio::spawn(async move {
    if let Err(e) = update_audio_cue(&response).await {
        tracing::warn!("Background audio failed: {e}");
    }
});
```

## Consequences
- Player sees narrator response immediately (~2-5s).
- Media arrives asynchronously (images and audio follow seconds later).
