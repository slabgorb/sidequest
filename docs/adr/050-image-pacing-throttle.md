---
id: 50
title: "Image Pacing Throttle"
status: accepted
date: 2026-04-01
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: [14]
tags: [media-audio]
implementation-status: live
implementation-pointer: null
---

# ADR-050: Image Pacing Throttle

> Retrospective — documents a decision already implemented in the codebase.
>
> **Implementation notes (2026-04-26):** The Rust impl referenced in §Decision did not survive ADR-082's Python port and was re-implemented as a 1:1 Python port (Story B of the S4-PERF playtest follow-up). The current implementation lives at `sidequest-server/sidequest/server/image_pacing.py` and is wired into `WebSocketSessionHandler._maybe_dispatch_render` BEFORE render-id allocation, so suppressed renders never reach the daemon. Both the `allow` and `suppress` branches publish a `render.throttle_decision` watcher event so the GM panel can verify the throttle is engaged. Mid-session slider UI (`ImagePacingSlider.tsx`) and per-genre cooldown tuning are deferred to follow-up stories — defaults are 30s solo / 60s MP per §Decision.

## Context
Image generation is triggered server-side when narration passes the BeatFilter's drama-weight threshold (a separate concern from this ADR). Without rate limiting at the delivery layer, rapid mechanical turn sequences — combat rounds, skill checks, quick back-and-forth dialogue — can dispatch multiple image render requests in seconds. The client receives images faster than they can be meaningfully absorbed, and the daemon wastes GPU cycles on renders that are immediately superseded.

Two distinct suppression mechanisms exist: BeatFilter (generation layer, drama-weight-based) and ImagePacingThrottle (delivery layer, time-based). This ADR covers the throttle only.

## Decision
`ImagePacingThrottle` tracks the timestamp of the last dispatched render. Any render request within the cooldown window is suppressed without reaching the daemon. The cooldown is configurable per-session:

- Default solo: 30 seconds
- Default multiplayer: 60 seconds (turns resolve faster in group play, so the cooldown window is longer)

The GM (DM role) can force-trigger a render that bypasses the cooldown. The force-override does not reset the cooldown timer — the window continues from the previous render, so the GM's manual trigger doesn't shorten the next organic cooldown. This allows the GM to fill lull periods without disrupting the pacing rhythm.

Players can adjust the cooldown mid-session via `ImagePacingSlider.tsx`, which emits the new value over the live WebSocket connection.

```rust
// sidequest-server/src/render_integration.rs
impl ImagePacingThrottle {
    pub fn should_render(&self, now: Instant) -> bool {
        now.duration_since(self.last_render) >= self.cooldown
    }

    pub fn force_render(&self, now: Instant) -> bool {
        // Bypasses cooldown; does NOT update last_render
        true
    }

    pub fn record_render(&mut self, now: Instant) {
        self.last_render = now;
    }
}
```

## Alternatives Considered

**Fixed cooldown, no user control** — rejected: optimal cadence varies by genre pace, group size, and player preference. A horror one-shot benefits from more frequent images than a political intrigue session.

**BeatFilter only, no time-based throttle** — rejected: BeatFilter operates on narrative drama weight, which doesn't account for turn velocity. A sequence of high-drama but rapid turns (e.g., a chase with multiple checks per minute) would still flood the client.

**Client-side-only throttle** — rejected: the server would still dispatch render requests to the daemon and waste GPU time on suppressed images. The throttle must live server-side to protect daemon resources.

**Per-turn image suppression (render at most once per player turn)** — rejected: too coarse. In solo play with deliberate pacing, consecutive turns might each merit an image. Time-based throttling captures actual session cadence better than turn counting.

## Consequences

**Positive:**
- Daemon GPU utilization is bounded regardless of turn velocity.
- Client image experience is paced to human absorption speed, not mechanical turn speed.
- GM force-override preserves creative control without disrupting the throttle state.
- Multiplayer default (60s) naturally adapts to faster group turn resolution.

**Negative:**
- Two suppression layers (BeatFilter + PacingThrottle) interact. A high-drama beat that passes BeatFilter can still be suppressed by the throttle, potentially missing a cinematically important moment.
- The cooldown slider adds another mid-session configuration surface. Players who set it to 0 effectively disable the throttle.
- `force_render` not resetting the timer is a subtle behavior that could surprise a GM who uses it frequently and then wonders why organic renders are still delayed.

## Amendment (2026-05-31): Render-Trigger Classification Policy

This ADR governs the **cooldown layer** — the time-based delivery throttle that
suppresses renders within a window (`should_render` / `force_render` /
`record_render`). It deliberately does not say *which turns are worth rendering in
the first place*. This amendment records a separate, deterministic
**trigger-classification layer** that now sits **above** the cooldown, and relates the
two layers rather than duplicating either.

### What the original ADR left implicit

The §Decision throttle answers "may we render *now*, given timing?" It assumed an
upstream signal had already decided "this turn merits an image." In the live system
that upstream signal was a naked `visual is None` short-circuit: the dispatch fired
whenever the narrator happened to emit a `visual_scene`. Playtest 3 (Felix,
2026-04-19) exposed this as policy-free — roughly 6–8 renders across 71 turns with no
auditable rationale for *why those turns* (banter turns rendered while named-NPC
introductions did not). See
`sidequest-server/sidequest/server/render_trigger.py`.

### The trigger layer (Story 45-30)

`classify_trigger(...)` in
`sidequest-server/sidequest/server/render_trigger.py` is a **pure,
deterministic** gate that decides *whether the renderer should fire this turn at all*,
returning a priority-ordered `RenderTriggerReason`
(`render_trigger.py`):

```
BEAT_FIRE > SCENE_CHANGE > NPC_INTRO > ENCOUNTER_RESOLVED > NONE_POLICY
```

Inputs are already-extracted **structured** signals on `NarrationTurnResult` plus an
out-of-band `encounter_resolved_this_turn` boolean threaded from the
`narration_apply` seam — no regex, no prose inference
(`render_trigger.py`, `:87-90`). Critically, `visual_scene` presence is **not** a
signal; the docstring calls this out as the deliberate reversal of the old
`visual is None` behaviour (`render_trigger.py`).

**Priority rationale.** First match wins. `BEAT_FIRE` (any trope/momentum beat
resolved this turn, `render_trigger.py`) ranks above `NPC_INTRO`: when a beat
and an NPC introduction coincide, the beat is the render-worthy moment. The story's
own framing — "the introduction is the diamond, not the cigarette-sharing scene that
follows" — is captured in the `NPC_INTRO` comment (`render_trigger.py`):
only NPCs with `is_new=True` trigger; recurring NPCs (`is_new=False`) do not, because
the *first* appearance is the Diamond and subsequent reappearances are not.
`SCENE_CHANGE` compares the narrator's `result.location` against the
**pre-turn** snapshot location (`snapshot_location_before`); a brand-new game passes
`None`, so entering the world counts as a scene change
(`render_trigger.py`). `ENCOUNTER_RESOLVED` is the lone signal sourced from the
`narration_apply` seam rather than orchestrator output (`render_trigger.py`).
`NONE_POLICY` is the explicit "no trigger this turn" terminal — an observable
*decision not to render*, not an absence (`render_trigger.py`).

### How the two layers compose

The trigger layer answers **"is this turn render-worthy?"**; ADR-050's cooldown then
answers **"and may we render now, given pacing?"** A turn must clear the trigger gate
(non-`NONE_POLICY`) *and* the cooldown window to actually dispatch. The GM
`force_render` bypass documented in §Decision operates on the **cooldown** layer — it
overrides timing, not the trigger classification — so the two controls remain
orthogonal: trigger says *what* is worth showing, cooldown says *how often*.

### Why this is an explicit, observable contract

The module docstring grounds the design in **ADR-014 (Diamonds and Coal)** and the
**OTEL Observability Principle**: both "require an explicit, observable contract:
every render decision lands a watcher event the GM panel can audit"
(`render_trigger.py`). The `RenderTriggerReason` values are **wire literals** —
they ship in the `render.trigger` watcher event `reason` field, the GM panel filters
on them, and renaming one is a wire-breaking change (`render_trigger.py`). This
makes the render-selection decision a first-class lie-detectable subsystem rather than
an implicit side effect, exactly as ADR-014 frames the Diamond/Coal distinction this
trigger encodes.

**Relationship summary:** ADR-050 owns the cooldown (time-based suppression);
this amendment records the trigger-classification layer above it, motivated by
ADR-014 (Diamonds and Coal) and made observable per the OTEL principle. The two
relate — gate then throttle — and do not duplicate.
