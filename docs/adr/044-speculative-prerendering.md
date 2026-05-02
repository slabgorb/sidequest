---
id: 44
title: "Speculative Prerendering During TTS Playback"
status: historical
date: 2026-04-01
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: [76]
tags: [media-audio]
implementation-status: retired
implementation-pointer: null
---

# ADR-044: Speculative Prerendering During TTS Playback

> **HISTORICAL 2026-05-02 — TTS DEPRECATED, FEATURE GONE.**
>
> TTS has been completely deprecated in SideQuest. The entire premise
> of this ADR (use the TTS playback window as free GPU render time)
> no longer applies because there is no playback window to hide
> behind. The `PrerenderScheduler` / `WasteTracker` are not part of
> the Python port. Player-perceived image latency is now sequential
> (narration arrives → image lazy-loads after the daemon round-trip)
> and is addressed via direct render-pipeline tuning rather than
> speculation.
>
> **Re-labeled from `superseded` to `historical` 2026-05-02.** The
> original re-label cited ADR-076 as superseder, but ADR-076 (post-
> TTS protocol cleanup) does not replace this ADR's design — it just
> happened to land in the same TTS-removal sweep. Per ADR-088: the
> correct label is `historical` ("describes a feature that no longer
> exists"), not `superseded` (which requires a successor that
> replaces the design). ADR-076's `supersedes: [44]` claim has been
> dropped to match.
>
> If post-TTS speculative prerendering ever becomes interesting
> again — e.g., predicting renders during the gap between narration
> turns regardless of audio — write a fresh ADR with current context.
> Do not revive this one.
>
> See [ADR-076](076-narration-protocol-collapse-post-tts.md) for the
> post-TTS protocol cleanup that surrounded this re-labeling.

> Retrospective — documents a decision already implemented in the codebase.

## Context
Flux image generation takes 5-20 seconds on the dev machine. TTS narration audio takes 5-15 seconds to play. These windows overlap — while the player is listening to the narrator, the GPU is idle waiting for the next scene context. On-demand rendering after narration ends produces a visible hold: voice stops, blank screen for 15 seconds, then image appears. This breaks immersion at the worst moment (scene transitions). The system needed a way to use the TTS playback window as free GPU render time.

## Decision
A `PrerenderScheduler` submits speculative image render jobs during TTS playback, predicting the next scene from available context: combat state, destination location, active NPC, and genre art style. If the prediction matches when narration ends, the image is already rendered — perceived zero latency.

A `WasteTracker` monitors the hit rate and self-disables speculation if it drops below a configurable threshold (default 30%). This prevents runaway GPU waste when scene context is unpredictable.

```rust
// PrerenderContext carries the prediction parameters
pub struct PrerenderContext {
    pub combat_state: Option<CombatState>,
    pub destination: Option<LocationId>,
    pub active_npc: Option<NpcId>,
    pub art_style: ArtStyle,
}

// WasteTracker disables speculation below threshold
pub struct WasteTracker {
    pub hits: u32,
    pub misses: u32,
    pub threshold: f32, // default 0.30
}
```

Implemented in `sidequest-game/src/prerender.rs`: `PrerenderScheduler`, `PrerenderConfig`, `WasteTracker`.

## Alternatives Considered

- **Always prerender** — Wastes GPU on scenes that never appear. On a constrained GPU budget, speculative renders compete with real ones.
- **Never prerender (on-demand only)** — Produces a visible hold after narration ends. Breaks immersion at scene transitions.
- **User-triggered prerender** — Requires player to anticipate transitions. Breaks immersion by making the latency the player's problem.

## Consequences

**Positive:**
- Scene transitions feel instantaneous when prediction is correct.
- GPU is productively used during TTS playback instead of sitting idle.
- `WasteTracker` prevents the system from degrading overall render throughput when speculation mispredicts consistently.
- Threshold is configurable — can tune aggressiveness per hardware profile.

**Negative:**
- Mispredicted renders consume GPU time that could serve confirmed requests.
- Hit rate below 30% disables speculation entirely — scenes with high branching factor get no benefit.
- Adds scheduling complexity: the server must track "speculative" vs "confirmed" render jobs and cancel or promote them.
- Prediction accuracy depends on game state legibility at narration start, which is sometimes unavailable (mid-combat improvisation).
