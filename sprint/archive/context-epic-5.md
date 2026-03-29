# Epic 5: Pacing & Drama Engine — Tension Model, Drama-Aware Delivery, Beat Filter

## Overview

Port the dual-track tension model from the Python codebase and wire it into the Rust
orchestrator. This is the "game engine tuning" work that emerged from extensive
playtesting in sq-2 — it makes combat feel cinematic by tracking dramatic weight and
using it to drive narration length, text delivery speed, and media generation decisions.

Without this, every turn feels the same. The narrator writes the same length of text
whether a character just opened a door or landed a killing blow. The drama engine fixes
that by computing a single `drama_weight` value (0.0-1.0) each turn and feeding it to
every downstream consumer: narrator prompt, text delivery mode, beat filter, and media
pipeline.

## Background

### The Problem This Solves

Combat in tabletop RPGs has a pacing problem. Most turns are routine — attack, miss,
attack, hit for small damage. A few turns are extraordinary — critical hits, killing
blows, death saves. Without pacing awareness, the AI narrator treats them all equally,
producing flat, monotonous sessions.

The Python implementation solved this with two independent tension tracks that combine
into a single drama weight. The result: boring stretches build anticipation (gambler's
ramp), dramatic moments get cinematic treatment, and the system self-corrects when
things go quiet for too long.

### Python Reference Code

| Rust Concept | Python Source | What to Port |
|--------------|--------------|-------------|
| TensionTracker | `sq-2/sidequest/game/tension.py` | Dual-track model, spike injection, decay |
| Combat event classification | `sq-2/sidequest/game/tension.py:classify_event()` | Boring/dramatic categorization |
| Drama weight computation | `sq-2/sidequest/game/tension.py:compute_weight()` | max() combination, decay curve |
| Pacing hints | `sq-2/sidequest/game/tension.py:get_pacing_hint()` | Sentence count guidance |
| Drama-aware delivery | `sq-2/sidequest/voice/delivery.py` | INSTANT/SENTENCE/STREAMING modes |
| Quiet turn detection | `sq-2/sidequest/game/tension.py:check_escalation()` | Boring streak threshold, beat injection |

### Design Documents

| Document | Key Content |
|----------|-------------|
| `sq-2/docs/prd-combat-pacing.md` | Product requirements, playtesting observations |
| `sq-2/docs/adr-dual-track-tension-model.md` | Why two tracks, how they combine |
| `sq-2/docs/adr-drama-aware-delivery.md` | Text reveal mode breakpoints |
| `sq-2/docs/adr-pacing-detection.md` | Quiet turn counting, escalation beats |

### What Epic 2 Delivers (prerequisite)

| Component | What's Done |
|-----------|-------------|
| **Combat system** | CombatState, turn resolution, HP tracking (story 2-7) |
| **Orchestrator** | Turn loop that produces narration and applies patches |
| **State patches** | CombatPatch with damage, status effects, outcomes |

The drama engine observes combat outcomes from Epic 2 and injects pacing metadata into
the turn pipeline.

## Technical Architecture

### Dual-Track Tension Model

```
Track 1: ACTION TENSION (gambler's ramp)
──────────────────────────────────────────
  boring_streak increments on each "boring" turn (miss, low damage, no status change)
  action_tension = min(boring_streak / ramp_length, 1.0)
  Resets to 0 on any dramatic event

  Intuition: "Something HAS to happen soon" — the longer nothing happens,
  the more the system nudges toward drama

Track 2: STAKES TENSION (HP-based)
──────────────────────────────────────────
  stakes_tension = 1.0 - (lowest_friendly_hp_ratio)
  Pure function of current game state — no memory

  Intuition: "Someone might die" — proximity to character death drives tension

Combination:
──────────────────────────────────────────
  drama_weight = max(action_tension, stakes_tension)
  Range: 0.0 (totally calm) to 1.0 (peak drama)

  Either track alone can drive drama to maximum. They don't compete; they cooperate.
```

### Event Spike Injection

```
Combat events inject instantaneous tension spikes that decay over subsequent turns:

  Event            Spike   Decay Rate
  ─────────────    ─────   ──────────
  CriticalHit      0.8     0.15/turn
  KillingBlow      1.0     0.20/turn
  DeathSave        0.7     0.15/turn
  FirstBlood       0.6     0.10/turn
  NearMiss         0.5     0.10/turn
  LastStanding     0.9     0.20/turn

  drama_weight = max(action_tension, stakes_tension, decaying_spike)

  Spikes ensure that a killing blow feels dramatic even if HP ratios are fine
  (e.g., the enemy died, not the player).
```

### Drama-Aware Delivery

```
drama_weight      Delivery Mode     Text Reveal Behavior
──────────────    ─────────────     ────────────────────
  < 0.30          INSTANT           Full text appears at once
  0.30 - 0.70     SENTENCE          Text reveals sentence by sentence
  > 0.70          STREAMING         Text streams word by word (typewriter)

  Genre packs can override these breakpoints.
```

### Narrator Length Targeting

```
drama_weight  ──►  target sentence count

  0.0  ──►  1 sentence   ("You miss.")
  0.2  ──►  2 sentences
  0.4  ──►  3 sentences
  0.6  ──►  4 sentences
  0.8  ──►  5 sentences
  1.0  ──►  6 sentences  ("The blade finds the gap in the dragon's scales...")

  Linear interpolation: sentences = 1 + floor(drama_weight * 5)
  Injected into narrator prompt as a soft constraint.
```

### Data Flow Through Turn Pipeline

```
CombatState (from Epic 2)
      │
      ▼
TensionTracker.observe(combat_outcome)  ◄── 5-1, 5-2
      │
      ├── classify event (boring / dramatic)
      ├── update boring_streak
      ├── compute stakes_tension from HP ratios
      ├── apply event spike if dramatic
      ├── decay previous spike
      │
      ▼
drama_weight = compute()  ◄── 5-3
      │
      ├──► PacingHint { sentences, delivery_mode }  ◄── 5-4, 5-5
      │         │
      │         ├──► narrator prompt (sentence count guidance)  ◄── 5-7
      │         └──► client delivery mode (INSTANT/SENTENCE/STREAMING)
      │
      ├──► quiet_turn_check()  ◄── 5-6
      │         │
      │         └──► inject escalation beat hint into narrator prompt
      │
      └──► beat filter threshold (Epic 4, 4-3)
                image render only if drama_weight > render_threshold
```

### Key Types

```rust
pub struct TensionTracker {
    boring_streak: u32,
    last_event_spike: Option<(CombatEvent, f64)>,
    action_tension: f64,
    stakes_tension: f64,
    ramp_length: u32,           // boring turns to reach 1.0 (default: 8)
    spike_decay_age: u32,       // turns since last spike
}

pub enum CombatEvent {
    CriticalHit,
    KillingBlow,
    DeathSave,
    FirstBlood,
    NearMiss,
    LastStanding,
}

pub struct PacingHint {
    pub drama_weight: f64,
    pub target_sentences: u8,
    pub delivery_mode: DeliveryMode,
    pub escalation_beat: Option<String>,
}

pub enum DeliveryMode {
    Instant,     // drama_weight < 0.30
    Sentence,    // 0.30 <= drama_weight <= 0.70
    Streaming,   // drama_weight > 0.70
}

/// Genre-tunable breakpoints
pub struct DramaThresholds {
    pub sentence_delivery_min: f64,    // default 0.30
    pub streaming_delivery_min: f64,   // default 0.70
    pub render_threshold: f64,         // default 0.40
    pub escalation_streak: u32,        // default 5
    pub ramp_length: u32,              // default 8
}
```

## Story Dependency Graph

```
2-7 (combat system)
 │
 └──► 5-1 (TensionTracker struct — dual-track model)
       │
       ├──► 5-2 (combat event classification, boring_streak)
       │     │
       │     └──► 5-3 (drama weight computation, spike injection + decay)
       │           │
       │           ├──► 5-4 (pacing hints — sentence count guidance)
       │           │     │
       │           │     └──► 5-7 (wire into orchestrator turn pipeline)
       │           │
       │           └──► 5-5 (drama-aware delivery modes)
       │                 │
       │                 └──► 5-8 (genre-tunable thresholds)
       │
       └──► 5-6 (quiet turn detection, escalation beat injection)
```

## Deferred (Not in This Epic)

- **Player-facing tension UI** — Displaying a tension meter or mood indicator in the
  React client. The drama engine is server-side; client visualization is a follow-up.
- **Multi-encounter tension memory** — Carrying tension across encounters (e.g., the
  second fight in a dungeon starts with residual tension). Currently resets per encounter.
- **NPC-specific tension tracking** — Tracking tension per NPC rather than globally.
  Useful for branching narratives but not needed for combat pacing.
- **Automated playtesting** — Using the tension model to score session quality
  programmatically. Related to Epic 3 (Game Watcher) but deferred.
- **Dynamic difficulty adjustment** — Using drama_weight to modify encounter difficulty.
  The engine observes pacing; it does not change game mechanics.

## Dependencies

### From Epic 2 (must complete first)
- Story 2-7: Combat system (5-1 depends on CombatState for HP ratios and combat
  outcomes that feed into the tension tracker)

### Cross-Epic Interaction
- Epic 4, Story 4-3 (beat filter): Consumes `drama_weight` to decide whether to
  generate images. The beat filter threshold is defined in this epic's DramaThresholds
  but applied in Epic 4's image pipeline.

## Success Criteria

During a playtest combat encounter:
1. Boring turns (miss, low damage) produce short narration (1-2 sentences) delivered
   instantly
2. As boring_streak grows, narration gradually lengthens (gambler's ramp effect)
3. A critical hit or killing blow produces long, cinematic narration (5-6 sentences)
   delivered in streaming mode
4. After a dramatic spike, tension decays naturally over subsequent turns
5. If 5+ turns pass with no drama, an escalation beat hint appears in the narrator
   prompt (e.g., "the environment shifts", "a new threat emerges")
6. When a character drops to low HP, stakes tension rises regardless of action
7. Genre packs can override all breakpoints — a horror genre might have lower thresholds
   for streaming delivery than a comedy genre
8. The drama_weight value is visible in Game Watcher telemetry (Epic 3 integration)
