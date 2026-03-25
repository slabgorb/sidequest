# ADR-005: Background-First Pipeline

> Ported from sq-2. Rust adaptation: `tokio::spawn` replaces `asyncio.create_task`.

## Status
Accepted

## Context
Player-perceived latency is dominated by the narrator agent response. All other work (rendering, audio, voice, state patching) can happen in the background.

## Decision
Only the text response is on the critical path. Everything else is spawned as a background `tokio` task.

### Critical Path (awaited)
- Intent classification (LLM router)
- Primary agent call (narrator/combat/dialogue)
- Voice digest summarization

### Background (spawned)
- Image rendering (via daemon)
- Audio cue selection
- Voice synthesis
- World state patching
- Speculative pre-generation

### Pattern
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

### Error Handling
Background task failures are logged as warnings, never propagated as errors. The game continues with degraded media rather than crashing.

## Consequences
- Player sees narrator response immediately (~2-5s)
- Media arrives asynchronously (images, audio follow seconds later)
- `--sync-pipeline` flag forces sequential execution for debugging
