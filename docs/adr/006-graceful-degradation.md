---
id: 6
title: "Graceful Degradation"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: [82]
tags: [core-architecture]
implementation-status: live
implementation-pointer: null
---

# ADR-006: Graceful Degradation

## Implementation status (2026-05-02)

The principle is fully live: **the game must never crash due to a media subsystem failure**. The narrator (Claude CLI) is the only non-negotiable dependency — everything else degrades.

Live signals in the Python tree:
- **`DaemonUnavailableError`** — raised when the media daemon is unreachable. Caught at the dispatch boundary; sessions continue. See `sidequest-server/sidequest/server/websocket_session_handler.py:3466` (rendering), `sidequest-server/sidequest/game/lore_embedding.py:32` (lore embedding).
- **`skipped_daemon_unavailable: bool`** — explicit "we tried, daemon was down, we skipped" signal that propagates through dispatch results so OTEL can record it. See `lore_embedding.py:79` and the dispatch wrapper in `dispatch/lore_embed.py:119`.
- **`render.skipped reason=daemon_unavailable`** OTEL events — the GM panel can see degradation rather than guessing whether a subsystem ran. See `websocket_session_handler.py:3105` and 3113.

**Philosophy shift since the original 2026-03-25 design.** The original ADR specified three-step fallback chains (primary → fallback → last-resort) for every subsystem. The codebase has converged on a simpler two-pattern model, partly because the original chains were masking real problems — see the cautionary comment at `websocket_session_handler.py:3192`: *"silent fallback is why grimvault renders looked generic."* This is consistent with CLAUDE.md's `<critical>No Silent Fallbacks</critical>` principle.

The two live patterns:
- **Skip-and-log** for daemon-dependent work (rendering, lore embedding). When the daemon is unavailable, raise `DaemonUnavailableError`, dispatch catches it, an OTEL skip event fires, the session continues. No mid-tier fallback — the operation is skipped cleanly.
- **Heuristic-as-primary** for tasks with a code-only path. `AudioInterpreter` (`sidequest-server/sidequest/audio/interpreter.py:219`, instantiated module-level at `session_handler.py:128`) is the live primary for audio cue extraction. The originally-specified `MusicDirector` agent is dormant — only `MusicDirectorDecision` (the Pydantic protocol model in `audio/protocol.py:18`) survives, and `rest.py:398` reports `"has_music_director": False`. If a MusicDirector agent is ever restored it would slot in as a primary above the interpreter; currently the interpreter *is* the primary.

The original 2026-03-25 fallback-chains table has been removed because every row I audited had rotted. Each media subsystem now owns its own degradation path at design time, and the codebase is the source of truth.

Drift watch — if any of the following happens, this ADR is wrong:
- A media subsystem failure is allowed to propagate up and break the narrator critical path.
- A silent fallback (no OTEL event, no log) is reintroduced for a daemon-down condition.

## Context
SideQuest depends on external services that may be unavailable. The Claude CLI (narrator) is non-negotiable — if it's down, the game is down. But media subsystems (renderer daemon, audio) must degrade gracefully. The game must never crash due to a media subsystem failure.

## Decision
Every media subsystem defines its own degradation path. Failures are logged, surfaced as OTEL events, and degraded — never propagated as fatal errors. Silent fallbacks are forbidden — see CLAUDE.md "No Silent Fallbacks."

> **Historical context (port era).** The 2026-03-25 form of this ADR specified three-step fallback chains (primary → fallback → last-resort) for every subsystem and gave a Rust example using `tokio` + `tracing`. The chains were trimmed in practice (silent fallbacks were masking real issues) and the implementation is now Python. The Rust example is preserved as a record of the original decision.

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
- Game is always playable, even with zero media services running.
- Degradation is visible in logs and OTEL but invisible to the player (except missing media).
- Each subsystem owns its own fallback path at design time; this ADR sets the principle, not the chains.
