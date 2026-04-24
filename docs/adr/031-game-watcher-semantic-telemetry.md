---
id: 31
title: "Game Watcher — Semantic Telemetry for AI Agent Observability"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [genre-mechanics]
implementation-status: live
implementation-pointer: null
---

# ADR-031: Game Watcher — Semantic Telemetry for AI Agent Observability

> New for Rust port. No Python equivalent — sq-2 uses ad-hoc logging.

## Context
SideQuest has an LLM adjudicating an RPG. Unlike a deterministic game engine, Claude makes
decisions that can't be unit tested: intent classification, narrative generation, state
mutations via JSON patches, trope progression. The operator needs to understand whether all
subsystems are being exercised and whether Claude's decisions are consistent with game state.

Traditional application telemetry (HTTP latency, error rates) doesn't answer these questions.
We need **semantic telemetry** — structured events that capture what was decided and why, not
just what was called and how long it took.

### Prior Art
Pennyfarthing (pf-1) uses OTEL to observe coding agents: tool invocations, durations,
enriched metadata (file paths, git status, diffs). Frame (FastAPI) receives OTEL via HTTP,
accumulates spans, and broadcasts to TUI/browser consumers via WebSocket. This pattern
works but observes agents from the outside. SideQuest observes from the inside — the Rust
code *is* the agent orchestrator, so it has direct access to all decision state. No
correlation problem, no race conditions.

### Design Principle: Human Judgment, Not AI Self-Judgment
The Game Watcher is a transparency tool for the human operator. It does not use a second
LLM call to validate the first one's output (the "God lifting rocks" problem — Claude can't
reliably judge whether Claude hallucinated). Automated checks flag anomalies; the human
makes the call.

## Decision

### Three-Layer Telemetry Model

**Layer 1 — Transport Telemetry** (tower-http, axum middleware)
Standard HTTP/WebSocket request tracing. Already covered by `tower-http::trace::TraceLayer`.
Not the focus of this ADR.

**Layer 2 — Agent Telemetry** (`tracing` spans on decision points)
Structured spans at every point where the system makes or executes a decision:

| Span | Fields | What It Captures |
|------|--------|-----------------|
| `intent_router.classify` | player_input, classified_intent, agent_routed_to, fallback_used | Was the input routed to the right agent? |
| `agent.invoke` | agent_name, token_count_in, token_count_out, duration_ms, raw_response_len | How much context did the agent see? How long did it take? |
| `json_extractor.extract` | extraction_tier (1/2/3), target_type, success | Did Claude's response parse cleanly or need fallback? |
| `state.apply_patch` | patch_type (world/combat/chase), fields_changed | What mutated? |
| `trope_engine.tick` | tropes_advanced, beats_fired, thresholds_crossed | Is narrative momentum working? |
| `context_builder.compose` | sections_count, total_tokens, zone_distribution | What context did the agent receive? |
| `state.compute_delta` | fields_changed, is_empty | What changed from the client's perspective? |

These use the `tracing` crate's `#[instrument]` macro and `Span::current().record()` for
deferred field population.

**Layer 3 — Narrative Telemetry** (async validation on the cold path)
Post-turn checks that compare agent output against game state. These run asynchronously
via `tokio::spawn`, never blocking the player-facing hot path.

| Check | What It Flags |
|-------|--------------|
| Entity reference | Narration mentions an NPC/item/location not in GameSnapshot |
| Inventory consistency | Patch adds/removes item without matching narration |
| Patch legality | HP exceeds max, dead NPC acts, invalid location transition |
| Trope beat alignment | Beat threshold crossed but narration doesn't reflect it |
| Subsystem exercise | Agent type hasn't been invoked in N turns (coverage gap) |

These emit `tracing::warn!` events into the same telemetry stream, tagged with
`component = "watcher"` and `check = "<check_name>"`.

### Core Data Structure: TurnRecord

After each turn, the orchestrator assembles a `TurnRecord` capturing everything the
validator needs, frozen at the moment the turn completed:

```rust
pub struct TurnRecord {
    pub turn_id: u64,
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub player_input: String,
    pub classified_intent: Intent,
    pub agent_name: String,
    pub narration: String,
    pub patches_applied: Vec<PatchSummary>,
    pub snapshot_before: GameSnapshot,
    pub snapshot_after: GameSnapshot,
    pub delta: StateDelta,
    pub beats_fired: Vec<(String, f32)>,  // (trope_name, threshold)
    pub extraction_tier: u8,
    pub token_count_in: usize,
    pub token_count_out: usize,
    pub agent_duration_ms: u64,
    pub is_degraded: bool,
}

pub struct PatchSummary {
    pub patch_type: String,       // "world", "combat", "chase"
    pub fields_changed: Vec<String>,
}
```

### Async Pipeline

```
Orchestrator (hot path)              Validator (cold path)
───────────────────────              ─────────────────────
  process_turn()
      │
  ... agent invoke, patch, delta ...
      │
  TurnRecord assembled
      │
  tx.send(record)  ─── mpsc ───►  rx.recv()
      │                                │
  broadcast to player                  ├─ entity_check()
  (no waiting)                         ├─ inventory_check()
                                       ├─ patch_legality_check()
                                       ├─ trope_alignment_check()
                                       ├─ subsystem_exercise_check()
                                       │
                                       └─ emit tracing events
                                          (warnings, validations)
```

The channel is bounded (`tokio::sync::mpsc::channel(32)`) — if the validator falls behind,
backpressure drops old records rather than blocking the turn loop.

### Watcher Endpoint

A dedicated WebSocket at `/ws/watcher` streams telemetry events to connected viewers.
This is separate from the player WebSocket (`/ws`) — it carries diagnostic data, not
game messages. Events are JSON-serialized `tracing` output filtered to game-relevant spans.

### Viewer Progression

1. **CLI tail**: `just watch` — tails structured JSON logs with colored output
2. **Subsystem heatmap**: Agent invocation histogram visible in the CLI output
3. **GM Mode panel**: React component in sidequest-ui (future, after Epic 2 complete)

## Consequences

### Positive
- Operator can observe all AI decision points in real time during playtesting
- Subsystem exercise gaps are immediately visible (agent X never called)
- Anomaly flags catch hallucinated state without blocking the game
- TurnRecord enables future session replay if persisted
- Uses existing `tracing` infrastructure — no new dependencies for Layer 2

### Negative
- `TurnRecord` clones two full `GameSnapshot`s per turn (memory cost)
- Validation checks require maintenance as game rules evolve
- Watcher WebSocket is an additional connection to manage

### Mitigations
- Snapshots use `Arc` where possible to share immutable data
- Validation checks are modular — add/remove independently
- Watcher endpoint is opt-in (only active when a client connects)

## Phasing

| Phase | Aligns With | Deliverable |
|-------|-------------|-------------|
| 1 | Story 1-12 | Structured `tracing` spans on server, JSON output, `RUST_LOG` filtering |
| 2 | Stories 2-5, 2-6 | Agent invocation telemetry, TurnRecord struct, mpsc channel |
| 3 | After 2-9 | Narrative validation checks, `/ws/watcher` endpoint |
| 4 | Post-Epic 2 | GM Mode panel in React UI, session replay |

## Related ADRs
- ADR-003: Session as actor (tokio task per connection)
- ADR-005: Claude CLI subprocess
- ADR-010: Intent-based agent routing
- ADR-011: World state JSON patches
- ADR-013: Lazy JSON extraction (3-tier fallback)
- ADR-018: Trope engine lifecycle
- ADR-026: Client state mirror
- ADR-027: Reactive state messaging
