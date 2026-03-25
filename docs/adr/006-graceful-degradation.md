# ADR-006: Graceful Degradation

> Ported from sq-2. Rust adaptation: `Result<T, E>` and `Option<T>` model fallback chains.

## Status
Accepted

## Context
SideQuest depends on external services (Claude CLI, renderer daemon, TTS daemon) that may be unavailable. The game must never crash due to a subsystem failure.

## Decision
Every subsystem has a defined fallback chain. Failures are logged and degraded, never propagated as fatal errors.

### Fallback Chains

| Subsystem | Primary | Fallback | Last Resort |
|-----------|---------|----------|-------------|
| Rendering | Daemon | Subprocess | Skip (no image) |
| Audio | MusicDirector | AudioInterpreter | Silence |
| Voice/TTS | Kokoro | Piper | Skip (text only) |
| Scene Detection | LLM extractor | Regex patterns | Skip render |
| Lore Retrieval | Embedding search | Static fragments | No lore context |
| Character Parse | Claude extraction | Keyword heuristics | Partial character |

### Rust Pattern
```rust
async fn resolve_audio_cue(narrative: &str, state: &GameState) -> Option<AudioCue> {
    // Try MusicDirector agent
    match music_director.select(narrative, state).await {
        Ok(cue) => return Some(cue),
        Err(e) => tracing::warn!("MusicDirector failed: {e}"),
    }

    // Fallback: heuristic interpreter
    match audio_interpreter.interpret(narrative) {
        Some(cue) => return Some(cue),
        None => tracing::debug!("No audio cue from interpreter"),
    }

    // Last resort: silence
    None
}
```

## Consequences
- Game is always playable, even with zero media services running
- Degradation is visible in logs but invisible to the player (except missing media)
- Each subsystem must define its own fallback chain at design time
