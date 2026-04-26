---
id: 50
title: "Image Pacing Throttle"
status: accepted
date: 2026-04-01
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
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
