# Epic 38: Dogfight Subsystem — Sealed-Letter Fighter Combat

## Overview

Extend `StructuredEncounter` (ADR-033) with a `SealedLetterLookup` resolution mode
that enables simultaneous-commit fighter combat. Inspired by the *Ace of Aces* book
game: two pilots each secretly commit a maneuver, then a cross-product lookup table
resolves the outcome mechanically — no geometry hallucination, no narrator improvisation.

The content layer (maneuvers, interaction table, descriptors, skill tiers) is already
authored and paper-validated by the GM agent in `sidequest-content/genre_packs/
space_opera/dogfight/`. This epic wires that content into the Rust engine, the narrator,
and the multiplayer session.

**Total:** 10 stories, 25 points. Two parallel tracks (code + content).

### Decision Record

ADR-077 (`docs/adr/077-dogfight-subsystem.md`) governs all architectural decisions.
Status: Proposed.

### Core Mechanic

```
Both pilots commit maneuver secretly (via TurnBarrier)
        ↓
Engine looks up (red_maneuver, blue_maneuver) in interaction table
        ↓
Per-actor descriptor deltas applied (bearing, range, aspect, energy, gun_solution)
        ↓
Narrator renders each pilot's cockpit POV from their updated descriptor
        ↓
Repeat until gun_solution triggers firing or escape achieved
```

## Background

### The Gap

Space opera ships `ship_combat` — capital-ship crew combat where the narrator selects
beats collectively. That models Star Destroyer vs. frigate drama. It does NOT model
fighter-class single-seat dogfighting where the fiction emerges from two independent,
hidden maneuver commits.

| Axis | `ship_combat` (existing) | Dogfight (proposed) |
|------|--------------------------|---------------------|
| Scale | Capital ship vs. capital ship | Fighter vs. fighter (1-2 pilots) |
| Decision | Crew collective, narrator-selected | Each pilot, secret commit |
| Resolution | Single beat → shared metric | Cross-product lookup of both commits |
| State | One metric + shared stats | Per-pilot descriptor (bearing, energy, gun solution) |
| Information | Full public | Sealed-letter then revealed |

### Why Not Pure Narration?

SOUL principle #12 (The Test): LLMs cannot reliably compose 3D rotations across turns.
By turn 5, improvised geometry drifts from any maneuver either pilot chose. The 16-cell
interaction table is the mechanical backbone that prevents this — every outcome is
authored, calibrated, and deterministic. The narrator renders FROM the descriptor, never
invents geometry outside it.

### Existing Content (Paper-Validated)

All content lives in `sidequest-content/genre_packs/space_opera/dogfight/`:

| File | What It Defines |
|------|-----------------|
| `descriptor_schema.yaml` | 11 MVP per-pilot state fields (bearing, range, aspect, closure, energy, gun_solution, etc.) + 4 future fields. Starting state: `merge` (head-on, close range, 60 energy). |
| `maneuvers_mvp.yaml` | 4-maneuver menu: `straight` (passive, recovers energy), `bank` (evasive, safe break), `loop` (offensive, +30 cost, reversal for gun solution), `kill_rotation` (space-only, flip-and-burn). Rock-paper-scissors class balance. |
| `interactions_mvp.yaml` | 16-cell lookup table (4x4). Each cell: descriptor deltas for both pilots + narration_hint prose. `gun_solution: true` gates firing opportunities. |
| `pilot_skills.yaml` | 4 tiers (Rookie→Ace) mapping progression affinities to maneuver availability and damage modifier. MVP defaults to Veteran (full 4-maneuver menu). |
| `playtest/duel_01.md` | Paper playtest scaffold with commit/reveal/narrate protocol. |

### Cross-Genre Skinning

Once `SealedLetterLookup` and `per_actor_state` exist on StructuredEncounter, any genre
can declare a dogfight-shaped confrontation:
- `low_fantasy` — dragon-mounted aerial jousting
- `victoria` — airship combat
- `neon_dystopia` — mech duel
- `road_warrior` — high-speed chase variant with vehicle maneuvers

The descriptor schema is genre-agnostic by design. `kill_rotation` is the only
space-opera-specific maneuver (vacuum physics); atmospheric genres substitute
with equivalent offensive options.

## Technical Architecture

### Extension Strategy (Additive Only)

Four additive extensions to existing types. Zero changes to existing confrontation
behavior. Every pack that doesn't declare a dogfight sees no difference.

**Extension 1 — `ResolutionMode` enum on `ConfrontationDef`** (38-1)
```rust
pub enum ResolutionMode {
    BeatSelection,        // existing behavior (default)
    SealedLetterLookup,   // new: simultaneous commit + cross-product lookup
}
```

**Extension 2 — `commit_options` and `interaction_table` on `ConfrontationDef`** (38-4)
Optional fields consumed only by `SealedLetterLookup`. Loaded from adjacent YAML
via `_from:` file pattern (new loader capability).

**Extension 3 — `per_actor_state` on `EncounterActor`** (38-2)
`HashMap<String, serde_json::Value>` — per-pilot scene descriptor. The narrator reads
it, the engine writes it via interaction table deltas.

**Extension 4 — New resolution handler** (38-5)
```rust
match confrontation.def.resolution_mode {
    BeatSelection => { /* existing path */ }
    SealedLetterLookup => {
        let commits = session.turn_barrier.drain_actor_commits();
        let cell = interaction_table.lookup(commits);
        apply_per_actor_delta(&mut actors, &cell);
        record_narration_hint(&cell.narration_hint);
    }
}
```

### Infrastructure Reuse Audit

| Need | Existing Infrastructure | Verdict |
|------|------------------------|---------|
| Encounter container | `StructuredEncounter` (ADR-033) | Reuse with additive extensions |
| Commit-and-reveal | `TurnBarrier` (Epic 13) | Reuse — pending scope check (38-3) |
| Narrator rendering | Unified narrator (ADR-067) | Reuse with prompt extension |
| Per-player views | `SharedSession.perception_filters` | Reuse for cockpit filter |
| Genre YAML loading | Genre pack loader | Extend with `_from:` sub-file pattern |
| Save/load | StructuredEncounter serde | Reuse; round-trip tested (38-2) |
| Mood wiring | MusicDirector `mood_override` | Reuse; declares `mood: dogfight` |
| Observability | OTEL infrastructure (ADR-031, 058) | Reuse; new span names only |

**Net new Rust code:** one enum, three optional struct fields, one match arm, one
loader extension, one OTEL span module. Everything else is reuse.

### OTEL Spans (Required)

| Span | Emitted When |
|------|-------------|
| `dogfight.confrontation_started` | New dogfight StructuredEncounter created |
| `dogfight.maneuver_committed` | Each actor commit arrives at barrier |
| `dogfight.cell_resolved` | Interaction table lookup completes |
| `dogfight.gun_solution_fired` | Actor with gun_solution fires |
| `dogfight.energy_depleted` | Actor energy below threshold |
| `dogfight.skill_tier_resolved` | Pilot tier determined at start |
| `dogfight.ace_instinct_used` | Tier-3 ace uses peek ability |

### Story Dependency Graph

```
Code Track (api):
  38-1 (ResolutionMode) ──┐
  38-2 (per_actor_state) ─┤
  38-3 (TurnBarrier) ─────┼──→ 38-5 (SealedLetterLookup handler) ──→ 38-6 (Narrator)
  38-4 (_from: loader) ───┘

Content Track (content, parallel with code):
  38-7 (hit_severity) ────── no code dependency
  38-8 (extend-return) ───── no code dependency
  38-9 (playtest calibrate) ─ informs 38-5 cell deltas
  38-10 (tail_chase state) ── proves generalization
```

38-1 through 38-4 are independent and parallelizable. 38-5 depends on all four.
38-6 depends on 38-5. Content stories (38-7 through 38-10) have no code blockers.

### Open Questions (Resolved During Implementation)

1. **TurnBarrier granularity (38-3):** Can barrier run at confrontation scope without
   breaking session-level turn accounting? If not, extend with scope parameter.
2. **`_from:` loader (38-4):** Does genre pack loader already support sub-file sourcing?
   If not, add as a general-purpose capability.
3. **`per_actor_state` validation:** Validate against descriptor_schema at load time
   (pre-check cell deltas reference valid fields), skip runtime validation.
4. **Damage model (38-7):** Content team extends interaction cells with `hit_severity`
   before 38-5 implementation.
5. **Extend-and-return (38-8):** Content-only post-turn reset rule, or engine rule
   with content override?

### Key Files

| File | Role |
|------|------|
| `docs/adr/077-dogfight-subsystem.md` | Architecture decision record |
| `sidequest-content/genre_packs/space_opera/dogfight/` | Content files (descriptors, maneuvers, interaction table, skills) |
| `sidequest-content/genre_packs/space_opera/rules.yaml` | Where `dogfight` confrontation entry will be added |
| `sidequest-api/crates/sidequest-game/src/encounter.rs` | StructuredEncounter — where extensions land |
| `sidequest-api/crates/sidequest-genre/src/models/rules.rs` | ConfrontationDef — where ResolutionMode is added |
| `sidequest-api/crates/sidequest-server/src/dispatch/` | Confrontation dispatch — where SealedLetterLookup handler lives |
| `sidequest-api/crates/sidequest-game/src/barrier.rs` | TurnBarrier — reused for commit-and-reveal |

### Risks

- **Interaction table balance:** 16-cell MVP is design-sensitive. Calibration tags
  (38-9) gate expansion to 8 maneuvers. This is a content risk, not an architecture risk.
- **TurnBarrier scope:** May be session-granular, not confrontation-granular. 38-3
  investigates before 38-5 depends on it.
- **Mutual gunline lethality:** 3 of 16 cells produce simultaneous gun solutions.
  May be over-lethal at low energy. Watch calibration tags.
- **`per_actor_state` typed-Value escape hatch:** Less safe than a named struct.
  Mitigated by schema validation at load time.

## Planning Documents

| Document | Location |
|----------|----------|
| ADR-077 | `docs/adr/077-dogfight-subsystem.md` |
| ADR-033 (parent) | `docs/adr/033-confrontation-engine.md` |
| ADR-067 (narrator) | `docs/adr/067-unified-narrator.md` |
| Paper playtest | `sidequest-content/genre_packs/space_opera/dogfight/playtest/duel_01.md` |
