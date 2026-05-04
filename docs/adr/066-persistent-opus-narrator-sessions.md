---
id: 66
title: "Persistent Opus Narrator Sessions"
status: accepted
date: 2026-04-04
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [agent-system, narrator]
implementation-status: live
implementation-pointer: null
---

# ADR-066: Persistent Opus Narrator Sessions

> **Status (2026-05):** `--resume` is wired into `ClaudeClient` (see
> `sidequest-server/sidequest/agents/claude_client.py`) and orchestrated via
> `Orchestrator._narrator_session_id`. Crash recovery and proactive rotation
> are governed by the **2026-05-04 amendment** at the bottom of this ADR.

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

## Amendment — Proactive Rotation and Crash Recovery (2026-05-04)

### Context

Playtest 3 (2026-05) ended in a server crash ~1h 45m into a single
narrator session. Root cause: the persistent `--resume` session grew
beyond the CLI's context budget. The CLI returned a context-overflow
error mid-turn, and the orchestrator propagated it as an unhandled
failure rather than recovering.

§5 of this ADR already specified the recovery primitive — *"If `--resume`
fails, fall back to establishing a new session with a condensed recap
from the last save's narration history."* — but the rule was *reactive
on CLI failure only* and was not implemented as a catching error path.
The playtest crash was the predictable outcome.

This amendment adds two missing rules: **proactive rotation** before the
CLI errors, and a **hardened reactive fallback** so a context-overflow
(or any narrator CLI error) is non-fatal.

### Decision

#### 7. Proactive Rotation (Watchdog)

The orchestrator tracks the **cumulative input tokens charged to the
narrator session** since establishment, summed from the per-turn
`usage` envelope already parsed by `ClaudeClient` (input + cache_create
+ cache_read).

When the cumulative count crosses a soft threshold, the orchestrator
calls `reset_narrator_session()` **between turns** — *before* sending the
next prompt. The next turn naturally re-establishes via the **Full**
prompt tier, with a recap spliced in (see §9 below).

**Default threshold: 700,000 input tokens** of the 1M Opus context
ceiling. Conservative because:
- The `usage` envelope under-reports tool-use overhead.
- Output tokens accumulate into the session's working set on the next
  turn's input cost.
- A 300k-token margin lets the recap-bearing rebuild turn run safely
  even if the next several turns are large.

The threshold is configurable via `SIDEQUEST_NARRATOR_TOKEN_BUDGET`
(env var) so playtest tuning does not require a code change.

#### 8. Hardened Reactive Fallback

The orchestrator wraps the `--resume` invocation in an error handler
that distinguishes:

| Error class | Action |
|---|---|
| Context-overflow / session-too-large | Reset session, retry the same turn via Full tier + recap, succeed silently. |
| Session not found / expired by CLI | Reset session, retry via Full tier + recap (existing §5 path). |
| Network / transient | Retry once on the same session. |
| Unknown narrator failure | Reset session, retry via Full tier + recap; if recovery also fails, surface a `narrator.unrecoverable` event to the GM panel and return a graceful in-fiction stall to the player ("the world holds its breath…"). |

A context-overflow error reaching the player as a hard failure is a
defect, not an expected outcome. Even with the watchdog set correctly,
the reactive path is the safety net.

#### 9. Recap Composition for Rebuild Turns

Session rebuilds — whether triggered proactively (§7) or reactively
(§8) — splice a **rebuild header** into the Full-tier prompt. The
header is composed from existing primitives:

- `SessionStore.generate_recap()` → "Previously On…" markdown from
  `narrative_log`.
- World state snapshot (already in Full tier).
- Narrative character sheets (already in Full tier).
- Active NPC dispositions and unresolved hooks (the *"baited but
  uneaten"* set — currently implicit in narrative log, may need
  promotion to a structured field; see Open Questions).

The header is wrapped in a **warm-reboot frame** that explicitly cues
the model:

```
[SESSION CONTINUATION]

The narration that follows is a continuation of an in-progress game.
You do not have verbatim memory of prior turns, but the world state
and recap below are authoritative. Resume narration in the established
tone and voice. Honor the hooks and NPC arcs in play.

[PREVIOUSLY ON]
{generate_recap() output}

[WORLD STATE]
{snapshot}

[CHARACTERS]
{narrative character sheets}
```

This frame does the work of telling the model *"this is a seam, not a
fresh start"* — without it, the rebuilt session can revert to
introductory prose ("As the dawn breaks over a land you have just
arrived in…") and break continuity in a way the players notice.

**Clarification (2026-05-04, post-45-47 spec-check):**

- The `[WORLD STATE]` and `[CHARACTERS]` blocks above are **illustrative
  content delivered via the Full-tier prompt**, not literal section
  markers the implementation must inject. World state and character
  sheets are already part of the Full-tier prompt registry; building
  the rebuild prompt with `tier=Full` carries them automatically. Only
  the `[SESSION CONTINUATION]` and `[PREVIOUSLY ON]` blocks are
  literal — the rest of the frame is shorthand for "the Full tier
  contents the model already has."

- The recovery turn sends the **entire composed Full-tier prompt as the
  `-p` user message** (with `system_prompt=None`), not split between
  `-p` and `--system-prompt` the way production's first turn does. This
  keeps the `[SESSION CONTINUATION]` cue adjacent to the player action
  in the model's working context. Production first-turn convention is
  preserved unchanged for the non-recovery path.

#### 10. Observability

Every rotation — proactive or reactive — emits an OTEL span:

```
narrator.session_rotated
  reason = token_threshold | cli_error | session_expired | unknown
  cumulative_tokens = <int>
  turn_number = <int>
  threshold = <int>          # only on proactive
  cli_error_signature = <str>  # only on reactive
  recap_chars = <int>
  rebuild_latency_ms = <int>
```

Rotations are first-class events in the GM panel. Sebastien sees them.
A rotation that fires too often (threshold too low) or too rarely
(threshold too high → CLI errors) is diagnosable from the dashboard
without log diving.

### Consequences

- **Crash class eliminated.** Out-of-context CLI errors no longer
  propagate as server crashes. Worst case is one slower rebuild turn
  (~10–12s instead of 6–8s) and a small tonal seam.
- **Predictable rotation cadence.** Keith picks the seam moment
  (threshold), not the CLI.
- **Recap is now load-bearing.** `generate_recap()` and the structured
  state it summarizes become part of the live narration loop, not just
  a save-load nicety. Quality of the recap directly determines quality
  of the seam. Plan to invest there.
- **OTEL surface area grows by one span class.** Cheap, valuable.
- **No new transport, no new CLI, no new ADR.** All reuse of primitives
  already specified in §5 and already shipped in `Orchestrator`,
  `ClaudeClient`, and `SessionStore`.

### Open Questions (deferred to implementation)

1. Should the **rebuild header** include the last 3–5 verbatim narration
   beats (final lines from `narrative_log`) to bridge the seam more
   tightly? Trade-off: token cost vs continuity smoothness.
2. Should *"baited but uneaten"* hooks (per SOUL.md) be promoted from
   implicit-in-narrative to a structured field on `GameState`? This
   ADR does not require it, but the recap quality argues for it.
3. Should the threshold be **adaptive** — track the average
   tokens-per-turn over the last N turns and rotate when the projected
   next-turn cost would cross the ceiling? Worth a follow-up if a
   static 700k proves too coarse.

### Implementation pointers

- Add `_cumulative_session_tokens: int` to `Orchestrator`, reset in
  `reset_narrator_session()`, incremented from the `usage` block in
  `run_narration_turn` after each successful narrator call.
- Add `_check_rotation_threshold()` called between the usage update
  and the next turn's prompt assembly.
- Wrap the narrator `await self._client.run(...)` calls in
  `_handle_narrator_error()` that classifies the failure and routes
  to the table in §8.
- Extend the Full-tier prompt builder to accept an optional
  `rebuild_header` argument; assemble per §9 when rotating.
- Add OTEL span per §10 from the existing telemetry layer
  (ADR-058 passthrough).
