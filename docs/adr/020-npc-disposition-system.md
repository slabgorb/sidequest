---
id: 20
title: "NPC Disposition System"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [game-systems]
implementation-status: partial
implementation-pointer: 87
---

# ADR-020: NPC Disposition System

> Ported from sq-2. Language-agnostic game mechanic.

## Decision
NPCs have a numeric `disposition` (integer) that maps to a qualitative `attitude` string. Agents see only the attitude; the world_state agent patches disposition with numeric deltas.

### Mapping
| Disposition | Attitude |
|------------|----------|
| > 10 | friendly |
| -10 to 10 | neutral |
| < -10 | hostile |

### Why Split
- **World state agent** thinks numerically: "player helped NPC, +5 disposition"
- **Narrator/NPC agents** think qualitatively: "the innkeeper is friendly"
- Threshold crossings create meaningful narrative moments without exposing math

### Rust Pattern
```rust
impl NPC {
    pub fn attitude(&self) -> &str {
        match self.disposition {
            d if d > 10 => "friendly",
            d if d < -10 => "hostile",
            _ => "neutral",
        }
    }
}
```

### Future
Thresholds should move to genre pack config. More granular attitudes (wary, grateful, terrified) are a known gap.

## Consequences
- NPCs evolve relationships naturally over time
- Trope beats can drive disposition changes between sessions
- Automatic re-derivation on every access ensures consistency

## Implementation status (2026-05-02)

The Rust era (`sidequest-api/crates/sidequest-game/src/disposition.rs`) implemented this ADR in full: an `Attitude` enum (`Friendly | Neutral | Hostile`), a `Disposition(i32)` newtype with `.attitude()` derivation, and an `apply_delta()` that emitted a `disposition.shifted` OTEL span flagging *attitude threshold crossings* — the load-bearing GM-panel signal that lets the lie-detector verify when an NPC actually flipped.

The 2026-04 port carried the **numeric layer** but not the qualitative split:

- `NPC.disposition: int = 0` with ±100 clamp lives in `sidequest/game/session.py`.
- Deltas are applied in `session.py:860-861` and an OTEL span is emitted on every change.
- A `_disposition_attitude(int) -> str` helper exists in `sidequest/server/dispatch/opening.py` — but only as local rendering-time derivation for the opening NPC list. Two call sites; no other agent goes through it.

Missing:

- A central `Attitude` enum used across the system. Agents currently see the raw int, contrary to this ADR's "agents see only the attitude" decision.
- Threshold-crossing detection in OTEL. The current span records the new number but does not flag when an NPC crosses Friendly↔Neutral↔Hostile — that is the GM-panel signal CLAUDE.md calls out as load-bearing.
- The "Future" extensions in this ADR (genre-configurable thresholds; granular attitudes like wary/grateful/terrified) — still aspirational.

Restoration is scheduled as **P1 RESTORE** in [ADR-087](087-post-port-subsystem-restoration-plan.md): "Scalar-only is below tabletop-DM baseline — fails the Keith-as-player test per CLAUDE.md." The decision in this ADR stands.
