# ADR-080: Unified Narrative Weight Trait

**Status:** Accepted
**Date:** 2026-04-14
**Epic:** TBD
**Deciders:** Keith
**Relates to:**
- ADR-014 (Diamonds and Coal) — parent decision; this ADR enforces its cross-cutting mandate
- ADR-018 (Trope Engine) — amended in practice; `tension_level` becomes live
- ADR-024 (Dual-Track Tension) — adjacent but orthogonal axis; stays independent
- ADR-033 (Confrontation Engine) — encounter subsystem participates via trait impl
- ADR-067 (Unified Narrator Agent) — narrator prose registers are a downstream consumer

## Context

ADR-014 declared `narrative_weight` (0.0–1.0) a first-class cross-cutting mechanic
controlling detail depth across inventory, rendering, audio, and narration. That
decision was accepted. Its cross-system scaling table named narration, rendering,
audio, and voice as consumers of the same axis.

Subsequent subsystems did not honor that mandate consistently. The current codebase
has narrative_weight wired through one pipeline and absent from every other:

**Live today:**

- `Item::narrative_weight: f32` — canonical, authored during inventory evolution
- `RenderSubject::narrative_weight() -> f32` — extracted from narration
- `BeatFilter::evaluate()` — consumes `subject.narrative_weight()` for image-render
  gating. Fully wired, functioning, semantics-correct.

**Dead or absent:**

- `TropeDefinition::tension_level: Option<f64>` — declared in YAML, **never read
  by any code path**. Verified: `TropeEngine::tick()` reads only `passive_progression`.
- `FiredBeat` — no weight field. The Troper agent injects all fired beats as equal
  `MANDATORY WEAVE`, flattening atmospheric beats and climactic beats into the same
  prose budget.
- `SceneDirective` — composes beats but exposes no unified weight axis.
- Narrator prose registers (coal / named / diamond) — do not exist. The Troper has
  no mechanism to tier prose density, sensory load, or specificity by per-beat
  importance.
- `Npc`, `StructuredEncounter` — no weight method; weight-aware consumers cannot
  distinguish a major NPC from a bartender, or a climactic confrontation beat
  from a warm-up exchange.

**Orthogonal axis, not unified here:**

- `TensionTracker` (`sidequest-game/src/tension_tracker.rs`, 780 LOC) tracks
  session-global pacing pressure (dual-track: action + stakes). That answers
  "how fast is the story moving right now," not "how much prose oxygen does
  this one thing deserve." A quiet emotional reveal is low-tension, high-weight.
  A frantic chase that's mechanical filler is high-tension, low-weight. These
  are genuinely different dimensions and both feed the narrator as independent
  signals.

## Decision

Introduce a single canonical `NarrativeWeight` abstraction and route every
weight-carrying content type and every weight-consuming subsystem through it.

### The Abstraction

New module: `sidequest-game/src/narrative_weight.rs`.

```rust
/// Canonical narrative weight — how much detail, prose budget, and render
/// attention a piece of content deserves. ADR-014 axis, unified.
#[derive(Debug, Clone, Copy, PartialEq, PartialOrd, Serialize, Deserialize)]
pub struct NarrativeWeight(f64);

impl NarrativeWeight {
    pub const COAL_CEILING: f64 = 0.5;
    pub const NAMED_CEILING: f64 = 0.7;

    pub fn new(value: f64) -> Self { Self(value.clamp(0.0, 1.0)) }
    pub fn value(&self) -> f64 { self.0 }
    pub fn tier(&self) -> NarrativeTier {
        if self.0 < Self::COAL_CEILING { NarrativeTier::Coal }
        else if self.0 < Self::NAMED_CEILING { NarrativeTier::Named }
        else { NarrativeTier::Diamond }
    }
    pub fn above(&self, threshold: f64) -> bool { self.0 >= threshold }
}

/// Discrete presentation tier derived from a NarrativeWeight value.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NarrativeTier {
    /// 0.0–0.5 — atmospheric, brief, skimmable. Unnamed particulars.
    Coal,
    /// 0.5–0.7 — earns identity, mid-oxygen prose. Named particulars.
    Named,
    /// 0.7–1.0 — full prose budget, expand the moment. Diamond particulars.
    Diamond,
}

/// Any content that carries narrative weight implements this trait.
///
/// This is the canonical interface for ADR-014's cross-cutting axis. All
/// consumers (rendering, narration prose registers, audio, voice) read
/// weight through this trait; all content types (items, beats, NPCs,
/// encounters, scenes, render subjects) expose weight through this trait.
pub trait Weighted {
    fn narrative_weight(&self) -> NarrativeWeight;
}
```

### Implementors

| Type | How Weight Is Computed |
|---|---|
| `Item` | Wraps the existing stored field in `NarrativeWeight`. Inventory evolution semantics unchanged. |
| `RenderSubject` | Wraps the existing stored field. `BeatFilter` semantics unchanged. |
| `FiredBeat` | `tension_level.unwrap_or(0.5) × (0.5 + 0.5 × beat.at)` — see formula section. First time `tension_level` does actual work. |
| `Npc` | Composite: disposition magnitude + story role tag + faction importance. All fields already exist on `Npc`/`CreatureCore`. |
| `StructuredEncounter` | Encounter-type floor + current `EncounterMetric` stakes. E.g. combat with metric < 0.3 tiers up to Diamond. |
| `SceneDirective` | Max over contained beat weights — scenes inherit from their loudest beat. |

### Consumers

| Consumer | Change |
|---|---|
| `BeatFilter::evaluate()` | Signature updated to consume `NarrativeWeight` instead of raw `f32`. Behavior byte-identical: `weight_threshold: f32` becomes a `NarrativeWeight` comparison via `.above()`. Image-render pipeline untouched. |
| Troper agent (`sidequest-agents/src/agents/troper.rs`) | New consumer. Switches on `beat.narrative_weight().tier()` to render beats in three prompt templates (coal / named / diamond). Replaces the current blanket `MANDATORY WEAVE` injection. |
| Narrator scene-level pacing | New consumer. Reads `SceneDirective::narrative_weight()` to allocate prose budget across beats within a scene. |
| Music, Audio, TTS voice | Optional follow-up consumers. Can be wired when appetite allows; not blocking this ADR. |

### FiredBeat Formula

```
weight = tension_level.unwrap_or(0.5) × (0.5 + 0.5 × beat.at)
```

Rationale: combines author-declared trope importance (`tension_level`, per-trope)
with position within the arc (`beat.at`, per-escalation). Both axes already exist
in YAML and loader. No schema change.

Behavior at tier boundaries:

| tension_level | beat.at | weight | tier |
|---|---|---|---|
| 0.9 | 0.25 | ~0.56 | Named (early beat of a major arc earns identity) |
| 0.9 | 1.0 | ~0.90 | Diamond (climactic beat of a major arc) |
| 0.5 | 0.5 | ~0.38 | Coal (mid-beat of a mid-arc, atmospheric) |
| 0.3 | 1.0 | ~0.30 | Coal (climax of a background arc, still minor) |
| 0.7 | 1.0 | ~0.70 | Diamond (climactic beat of a strong arc) |

The curve is author-calibration-sensitive. If playtest shows authors systematically
wanting a different mapping, the combiner is a single function to tune and does
not require schema or trait changes.

## Scope

This is abstraction-extraction and wiring of an existing decision. Not new
functionality, not new data, not new schemas.

**In scope:**

1. New module `sidequest-game/src/narrative_weight.rs` (~80 LOC)
2. `Weighted` trait implementations on `Item`, `RenderSubject`, `FiredBeat`,
   `Npc`, `StructuredEncounter`, `SceneDirective` (~200 LOC total)
3. `tension_level` consumed by `FiredBeat::narrative_weight()` — the dead field
   becomes live
4. Troper agent prose-register templates (coal/named/diamond) and tier-based
   prompt assembly (~100 LOC in `troper.rs`)
5. `BeatFilter` signature update to accept `NarrativeWeight` (~30 LOC,
   byte-identical semantics)
6. Integration test proving end-to-end wiring: `tension_level` declared in YAML
   flows through `FiredBeat::narrative_weight()` → Troper → narrator prompt in
   the correct register

**Not in scope (stays as-is):**

- `TensionTracker` — orthogonal axis, independent narrator input
- `DramaThresholds` — genre-pack pacing config
- Trope tick/progression logic — already correct
- `BeatFilter` decision semantics — preserved byte-for-byte
- Image render pipeline — untouched
- YAML schemas — no new fields; `tension_level` already exists
- Music/Audio/TTS weight consumption — optional follow-up, not blocking

## Consequences

**Positive:**

- ADR-014's cross-cutting mandate is finally wired end-to-end. Future subsystems
  inherit a single target to implement.
- `tension_level` becomes live. Author intent declared in YAML starts shaping
  narrator output for the first time.
- Troper agent gains prose registers, fixing the equal-weight injection problem
  where atmospheric beats and climactic beats competed for the same prose budget.
- Strong typing at the consumer boundary: passing a raw `f32` where
  `NarrativeWeight` is expected will fail at compile time.
- One canonical axis for all future weight-carrying additions. No parallel axes.

**Trade-offs:**

- Adds a trait-dispatch layer to several hot-path types. Negligible at runtime;
  all calls are monomorphized.
- Author-facing change: `tension_level` gains real meaning. Existing genre packs
  that left it unset (most of them) will compute `unwrap_or(0.5)` — a neutral
  default that keeps current behavior stable but invites authoring pass to
  actually tune tropes.
- Future tuning of the `FiredBeat` formula will change narrator behavior across
  all genres simultaneously. This is an advantage (single lever) and a risk
  (single point of failure). The formula is isolated in one function for
  tuning safety.

**Non-trade-offs worth naming:**

- This does NOT require a content migration. Tropes without `tension_level` get
  the 0.5 neutral default. Playtest will reveal which genres need an authoring
  pass.
- This does NOT deprecate `TensionTracker`. Pacing and weight are orthogonal.

## Implementation Notes

The refactor lands cleanly as a single story or a tightly-sequenced two-story
pair. The trait and implementations can land first; the Troper prose-register
consumer can land second with the new integration test as the wiring verification.

`BeatFilter` stays structurally unchanged — its `weight_threshold: f32` config
field loads from YAML and constructs a `NarrativeWeight` at use time. The
BeatFilter semantic is preserved: "suppress if subject weight below threshold."

Downstream effects (music intensity binding, voice tiering, scene-level prose
budget allocation in the narrator) are not scoped here. They become natural
follow-up work once the trait is live — any subsystem that wants to consume
weight now has one interface to read from, and any subsystem that wants to
produce weight has one interface to implement.
