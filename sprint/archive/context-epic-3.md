# Epic 3: Game Watcher — Semantic Telemetry

## Overview

Build an observability layer that lets the operator understand AI agent decisions during
live play. SideQuest has an LLM adjudicating an RPG — intent classification, narrative
generation, state mutations, trope progression are all Claude decisions that can't be
unit tested. The Game Watcher surfaces these decisions as structured telemetry for human
inspection.

This is NOT an automated validation system. It's a transparency tool. The human examines
traces and makes the judgment call (ADR-031: "God lifting rocks" principle).

## Background

### What Epic 2 Delivers (prerequisite)

| Component | What's Done |
|-----------|-------------|
| **Orchestrator** | Turn loop: input → intent → agent → narration → patch → broadcast |
| **Agent execution** | Claude CLI subprocess, prompt composition, JSON extraction |
| **State patches** | WorldStatePatch, CombatPatch, ChasePatch applied to GameSnapshot |
| **Trope engine** | Tick progression, beat firing at thresholds |
| **StateDelta** | Before/after snapshot comparison for client sync |

The Game Watcher observes all of the above without interfering with it.

### Prior Art: Pennyfarthing OTEL

Pennyfarthing (pf-1) observes coding agents via OTEL: tool invocations flow through
Frame (FastAPI) → WebSocket broadcast → TUI/browser consumers. Key differences:

| Aspect | Pennyfarthing | SideQuest Game Watcher |
|--------|---------------|----------------------|
| Observation point | External (intercepts OTEL logs) | Internal (is the orchestrator) |
| Correlation | Complex (match message stream to OTEL) | Direct (owns all state) |
| Telemetry focus | Tool execution (Read, Edit, Bash) | Agent decisions (intent, narration, patches) |
| Validation | Agent benchmarks (offline) | Narrative consistency (near real-time) |

### Key ADR

**ADR-031: Game Watcher — Semantic Telemetry for AI Agent Observability**
- Three-layer model: transport → agent → narrative telemetry
- TurnRecord struct as hot-path/cold-path contract
- tokio::mpsc async pipeline
- Human judgment design principle

## Technical Architecture

### Three Telemetry Layers

```
Layer 3: NARRATIVE TELEMETRY (async validation)
  Entity refs, patch legality, trope alignment, subsystem exercise
  Runs on cold path via TurnRecord channel
  Flags anomalies for human inspection

Layer 2: AGENT TELEMETRY (tracing spans)
  #[instrument] on all decision points
  Semantic fields: intent, agent, extraction tier, fields changed
  JSON output via tracing-subscriber

Layer 1: TRANSPORT TELEMETRY (tower-http)
  HTTP/WebSocket request tracing
  Standard middleware — not the focus of this epic
```

### Data Flow

```
Orchestrator (hot path)              Validator (cold path)
───────────────────────              ─────────────────────
  process_turn()
      │
  [agent spans emitted via tracing]
      │
  TurnRecord assembled
      │
  tx.send(record)  ─── mpsc ───►  rx.recv()
      │                                │
  broadcast to player                  ├─ patch_legality_check()
  (zero wait)                          ├─ entity_reference_check()
                                       ├─ subsystem_exercise_check()
                                       ├─ trope_alignment_check()
                                       │
                                       └─ emit tracing events
                                          + broadcast to /ws/watcher
```

### Key Type

```rust
pub struct TurnRecord {
    pub turn_id: u64,
    pub timestamp: DateTime<Utc>,
    pub player_input: String,
    pub classified_intent: Intent,
    pub agent_name: String,
    pub narration: String,
    pub patches_applied: Vec<PatchSummary>,
    pub snapshot_before: GameSnapshot,
    pub snapshot_after: GameSnapshot,
    pub delta: StateDelta,
    pub beats_fired: Vec<(String, f32)>,
    pub extraction_tier: u8,
    pub token_count_in: usize,
    pub token_count_out: usize,
    pub agent_duration_ms: u64,
    pub is_degraded: bool,
}
```

## Story Dependency Graph

```
2-5 (orchestrator turn loop)
 │
 └──► 3-1 (agent telemetry spans)
       │
       ├──► 3-2 (TurnRecord + mpsc)
       │     │
       │     ├──► 3-3 (patch legality)
       │     ├──► 3-4 (entity references)
       │     │     │
       │     │     └──► 3-8 (trope alignment)
       │     └──► 3-5 (subsystem exercise)
       │
       └──► 3-6 (watcher WebSocket)
             │
             ├──► 3-7 (CLI watcher)
             └──► 3-9 (GM Mode panel, also depends on 2-9)
```

## Deferred (Not in This Epic)

- **Session replay** — Persisting TurnRecords for post-session playback. TurnRecord
  design enables this; implementation deferred.
- **SQLite audit log** — Writing validation results to database for querying. Could
  share the persistence layer from story 2-4.
- **External LLM judge** — Using a different model to score session quality. This is
  a benchmarking concern, not a live observability concern.
- **Automated remediation** — Auto-correcting invalid patches. The watcher flags;
  the human decides.

## Dependencies

### From Epic 2 (must complete first)
- Story 2-5: Orchestrator turn loop (3-1 depends on this)
- Story 2-8: Trope engine runtime (3-8 depends on this thematically)
- Story 2-9: End-to-end integration (3-9 depends on this)

### From Epic 1
- Story 1-12: Structured logging foundation (tracing-subscriber init)

## Success Criteria

During a playtest, the operator can:
1. Run `just watch` and see a live stream of agent decisions per turn
2. See which subsystems have been exercised and which haven't
3. Get flagged when a patch violates game rules (HP > max, dead NPC acts)
4. Get flagged when narration references entities not in game state
5. See trope progression and beat firing in the telemetry stream
6. Inspect game state at any point via the watcher stream
7. (Future) Toggle a GM Mode panel in the React UI for integrated viewing
