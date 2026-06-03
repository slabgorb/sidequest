---
id: 18
title: "Trope Engine"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [game-systems]
implementation-status: live
implementation-pointer: "sidequest-server/sidequest/game/trope_tick.py + trope_time_skip.py — all four pillars wired at _execute_narration_turn (per ADR body 'Remaining gaps: None')"
---

# ADR-018: Trope Engine

> Ported from sq-2. Language-agnostic narrative system.

## Context
Stories need momentum. Genre-defined narrative patterns (tropes) provide a skeleton that ensures the story progresses even during quiet periods.

## Decision
Tropes are genre-defined narrative patterns that track a lifecycle with escalation beats.

### Lifecycle
```
DORMANT → ACTIVE → PROGRESSING → RESOLVED
```

### Escalation Beats
Each trope defines beats that fire at progression thresholds:

```yaml
tropes:
  reluctant_hero:
    description: "Hero resists the call to adventure"
    beats:
      - threshold: 0.25
        description: "First refusal of the quest"
        npcs_involved: ["mentor"]
        stakes: "low"
      - threshold: 0.50
        description: "Consequences of inaction become visible"
        stakes: "medium"
      - threshold: 0.75
        description: "Personal cost forces commitment"
        stakes: "high"
      - threshold: 1.0
        description: "Full acceptance of the quest"
        stakes: "climactic"
    rate_per_turn: 0.02
    rate_per_day: 0.05  # between-session advancement
```

### Passive Advancement
Tropes tick forward via `rate_per_turn` during gameplay and `rate_per_day` between sessions, ensuring they don't stall even if the player ignores them.

### Beat Deduplication
`fired_beats: HashSet<(String, f32)>` prevents the same beat from firing twice.

## Consequences
- Stories have built-in momentum independent of player choices
- Genre packs define narrative pacing without code
- Between-session advancement keeps the world "alive"

## Implementation status (2026-05-13)

The Rust era (`sidequest-api/crates/sidequest-game/src/trope.rs`) implemented this ADR in full: `TropeStatus::{Dormant, Active, Progressing, Resolved}`, `fired_beats: HashSet`, `tick()` driving `rate_per_turn`, `advance_between_sessions()` driving `rate_per_day`.

The 2026-04 port to Python carried the **data structures** (`sidequest/genre/models/tropes.py`: `TropeDefinition`, `TropeEscalation`, `PassiveProgression`) and the **YAML schemas** (every genre pack's `tropes.yaml`) but did not port the engine. Story 45-27 restored the in-session engine at `sidequest-server/sidequest/game/trope_tick.py` (417 lines), wired at `_execute_narration_turn` in `websocket_session_handler.py`. The unified narrator (ADR-067) still emits `beat_selections`; `narration_apply.py` records them — the tick engine handles passive advancement and lifecycle around that.

### Restored (no longer gaps)

- **Passive `rate_per_turn` advancement** — `trope_tick.py` Pass A; `turn.tropes` span fires every tick.
- **Beat-fire dedup** — implemented as `beats_fired: int` counter advancing through `tdef.escalation` (different shape from the Rust `HashSet<(String, f32)>`, but functionally equivalent — same beat cannot fire twice).
- **Activation gating** — dormant→progressing transitions are gated by a simultaneous-active cap and a post-fire cooldown window, emitting `trope.cooldown_blocked` / `trope.cap_blocked` for GM-panel visibility.
- **Implicit resolution** — a trope with all beats fired AND progress at 1.0 transitions to `resolved` and emits `trope_resolve`.

### Remaining gaps

None — all four pillars are wired.

### Implementation update (2026-05-13)

Story 50-4 closed the `rate_per_day` gap. The narrator now emits `days_advanced: int` in the `game_patch` block (CRITICAL TIME RULE in `output_only.md`); `tick_tropes` runs a new Pass A2 (`sidequest/game/trope_time_skip.py`) between Pass A and Pass B; every progressing trope advances by `rate_per_day * clamp(days_advanced, 0, 14)`; every crossed beat threshold fires and is queued as a `TimeSkipBeatEvent` in `snapshot.pending_time_skip_summary`; the next narrator prompt renders these as a `## TIME-SKIP CONTEXT` block (Early attention zone) and clears the queue (one-shot lifecycle). A distinct `trope.time_skip` OTEL span carries `days_requested`, `days_applied`, `clamped`, `tropes_affected`, `tropes_skipped_zero_rate`, `beats_fired_count`, and `resolved_during_skip` for GM-panel observability. Persistence rides the existing whole-snapshot JSON column — no schema migration.

### Drift between ADR text and implementation

- **Lifecycle is three-state, not four.** This ADR's prose specifies `DORMANT → ACTIVE → PROGRESSING → RESOLVED`. The restored engine uses `dormant → progressing → resolved` — the `ACTIVE` state was collapsed into `PROGRESSING` during restoration because the distinction was never load-bearing (beats fire on the progressing edge regardless). The code is the source of truth; this ADR's text is the lagging document. The lifecycle diagram above should be read as illustrative of the lineage, not the current state machine.

Status downgraded from "all four pillars missing" (the prior 2026-05-02 reading) to "one mechanical gap + one documentation drift." [ADR-087](087-post-port-subsystem-restoration-plan.md) row 64 is correspondingly stale and is updated alongside this amendment.
