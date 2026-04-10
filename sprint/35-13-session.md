---
story_id: "35-13"
jira_key: "MSSCI-35-13"
epic: "MSSCI-35"
workflow: "tdd"
---
# Story 35-13: OTEL watcher events for chargen subsystems — stats, backstory, hp_formula + AudioVariation fallback

## Story Details
- **ID:** 35-13
- **Jira Key:** MSSCI-35-13
- **Epic:** MSSCI-35 (Wiring Remediation II — Unwired Modules, OTEL Blind Spots, Dead Code)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 3
- **Priority:** p1
- **Type:** chore

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-10T10:43:22Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-10T10:43:22Z | - | - |

## Story Context

This story adds OTEL watcher events to three chargen (character generation) subsystems that currently have zero observability:

1. **stats** — Character attribute calculation and advancement
2. **backstory** — Character history generation and narrative context
3. **hp_formula** — Hit point calculation and scaling

Plus: **AudioVariation fallback** — When the main audio variation path fails, emit a fallback event so the GM panel shows which subsystem recovered gracefully.

### Subsystem Locations

- **stats:** `sidequest-api/crates/sidequest-game/src/chargen/stats.rs`
- **backstory:** `sidequest-api/crates/sidequest-game/src/chargen/backstory.rs`
- **hp_formula:** `sidequest-api/crates/sidequest-game/src/chargen/hp_formula.rs`
- **AudioVariation:** `sidequest-api/crates/sidequest-daemon-client/src/audio_variation.rs` (fallback handler)

### Acceptance Criteria

1. **stats subsystem**: Emit OTEL span on attribute calculation (ability scores, modifiers)
2. **backstory subsystem**: Emit OTEL span on narrative block generation
3. **hp_formula subsystem**: Emit OTEL span on HP calculation and hit point maximum computation
4. **AudioVariation fallback**: Emit OTEL event when audio variation generation fails and system falls back to default

All events must:
- Use structured OTEL telemetry from `sidequest-telemetry` crate
- Include relevant context (character id, subsystem state, values computed)
- Be visible in the GM panel watcher
- Not impact performance of the chargen flow

### Dependencies

- Related stories: 35-8 (beat_filter, scene_relevance), 35-9 (NPC subsystems)
- Related epic: Epic 35 (Wiring Remediation II)
- Must follow OTEL watcher pattern established in 35-8 and 35-9
- Telemetry infrastructure: `sidequest-telemetry` crate with watcher macros

### Implementation Notes

Reference the completed 35-9 story for the OTEL watcher pattern:
- Use `#[watcher_span]` macro or manual span creation
- Include subsystem-specific fields in span attributes
- Ensure fallback paths emit clear failure/recovery events

## Delivery Findings

No upstream findings.

## Design Deviations

None recorded yet.
