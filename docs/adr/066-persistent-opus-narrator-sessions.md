# ADR-066: Persistent Opus Narrator Sessions

## Status
Accepted

## Context

Turn latency in playtest session 2 averaged ~22s. The primary bottleneck is prompt
reconstruction: every narrator call via `claude -p` rebuilds ~30k tokens of system
context (genre rules, world state, room graph, character sheet, narration history)
from scratch. The Claude CLI then prefills this entire context before generating.

A spike on 2026-04-04 proved that `claude -p --resume <session-id>` carries full
conversation state across calls, with server-side caching reducing prefill cost.
Results over 3 turns:

| Turn | Latency | Cache read | Cache create | Notes |
|------|---------|------------|--------------|-------|
| 1 | 9.4s | 0 | 15,519 | Session establishment |
| 2 | 9.3s | 11,400 | 10,495 | Cache hit on resume |
| 3 | 6.4s | 11,400 | 10,742 | Warm cache, fastest |

The CLI auto-upgraded to `claude-opus-4-6[1m]` (1M context) on resume. At ~2k
tokens per turn, this supports 500+ turns per session — far beyond any realistic
play session (typically 30-100 turns).

Narration quality on Opus was markedly superior to Sonnet: character consistency
across turns, tonal memory, emergent personality arcs for NPCs. The barkeeper in
the spike developed a grudging-respect arc across 3 turns with zero prompting —
Opus inferred it from the conversation dynamics.

## Decision

### 1. Persistent narrator sessions via `--resume`

The narrator agent uses `--session-id <uuid>` on the first turn and `--resume <uuid>`
on all subsequent turns. The UUID is stored in the game session and persisted to SQLite
alongside the save file.

```rust
// First turn: establish session
let session_id = Uuid::new_v4();
Command::new("claude")
    .args(["-p", "--model", "opus",
           "--session-id", &session_id.to_string(),
           "--system-prompt", &system_prompt,
           "--output-format", "json",
           &action_prompt])
    .output().await

// Subsequent turns: resume
Command::new("claude")
    .args(["-p", "--resume", &session_id.to_string(),
           "--output-format", "json",
           &action_with_state_delta])
    .output().await
```

### 2. Model tier assignment

| Role | Model | Transport |
|------|-------|-----------|
| Narrator | Opus | `--resume` persistent session |
| Intent classification | Sonnet | `claude -p` (one-shot) |
| Inventory extraction | Sonnet | `claude -p` (one-shot) |
| Subject extraction | Sonnet | `claude -p` (one-shot) |
| Continuity validation | **Removed** | N/A |

Continuity validation is eliminated. The persistent Opus session maintains full
conversation context, making a separate Haiku consistency check redundant. This
removes one LLM round-trip (~5-15s) from the turn pipeline.

Satellite agents upgrade from Haiku to Sonnet for improved structured output
compliance (intent classification accuracy, inventory extraction reliability).

### 3. State injection protocol

Between turns, the engine injects state deltas as the action prefix rather than
rebuilding the full world context:

```
[STATE DELTA]
- Location changed: The Throat → The Junction
- HP: 8/11 → 5/11 (took 3 damage from trap)
- Inventory: +1 iron key
- Keeper awareness: 5 → 7

[PLAYER ACTION]
I examine the door to the north.
```

Static context (genre rules, room graph, character class, trope definitions) is
sent once at session establishment. Only changes are injected per turn.

### 4. State correction protocol

If the engine detects divergence between Claude's narrative and mechanical state:

```
[STATE CORRECTION]
The player does NOT have a torch — it was consumed 3 turns ago.
Current inventory: dagger, rope, 2 rations, iron key.
Narrate accordingly.
```

Corrections are injected as user messages before the player's action. The
persistent context means Claude will remember the correction for all subsequent
turns.

### 5. Session lifecycle

- **Create:** First WebSocket connect for a genre/world/player → new UUID, `--session-id`
- **Resume (same server):** Subsequent turns → `--resume` with stored UUID
- **Resume (reconnect):** Player disconnects, reconnects → UUID from SQLite, `--resume`
- **Permadeath:** Player dies → SQLite save deleted (ADR existing), session UUID discarded.
  Next connect starts a fresh session.
- **Session expiry:** If `--resume` fails (CLI-side session expired/cleaned up), fall back
  to establishing a new session with a condensed recap from the last save's narration history.

### 6. game_patch via tool_use (phase 2)

Replace the fenced ```` ```game_patch``` ```` block protocol with Claude's native tool_use:

```
--allowedTools "update_game_state"
```

The narrator calls `update_game_state` as a structured tool with typed fields
(location, items_gained, items_lost, npcs_met, mood, confrontation). The CLI
returns tool calls as structured JSON — no regex parsing, no block stripping,
no orphan text fragments. The entire category of "structured output leaking
into narration" bugs ceases to exist.

This is phase 2 — the persistent session works without it. But it's the natural
evolution: the narrator becomes a structured agent, not a text generator we scrape.

## Consequences

### Performance
- **Turn latency:** ~22s → ~6-10s (cache-warm resume + no continuity validation)
- **First turn:** ~9-10s (session establishment, no cache)
- **Token efficiency:** System prompt sent once, not 80x per session

### Quality
- **Narrative consistency:** Opus with full conversation context > Sonnet with reconstructed history
- **Character memory:** NPCs maintain personality arcs without explicit tracking
- **Structured output:** Sonnet satellite agents more reliable than Haiku for intent/extraction
- **Emergent behavior:** Opus may notice player patterns and adapt narration style unprompted

### Cost
- **Claude Max:** Flat-rate subscription. No per-token cost. Zero marginal cost per session.
- **Rate limits:** Monitor for daily/hourly ceilings under sustained play. Multiplayer
  (N concurrent sessions) may hit concurrency limits.

### Simplification
- **Kill:** `validate_continuity()` — the Haiku consistency checker (~400 LOC + dispatch wiring)
- **Kill:** `strip_fenced_blocks()` — replaced by tool_use (phase 2)
- **Simplify:** `build_prompt()` — system prompt once at session start, per-turn injection is just deltas
- **Simplify:** Narration history management — Claude has the full conversation natively

### Risks
- **Session expiry:** CLI may garbage-collect old sessions. Mitigated by fallback-to-recap.
- **Claude Max rate limits:** Unknown ceiling for sustained Opus usage. Monitor in playtest.
- **Debugging:** Conversation state lives on Claude's servers, not in our logs. May need
  `--output-format json` logging of each turn for post-mortem analysis.

## Supersedes

Amends **ADR-001** (Claude CLI Only): the CLI-only constraint remains, but the transport
evolves from stateless `claude -p` to stateful `claude -p --resume`. No Anthropic SDK
dependency introduced.
