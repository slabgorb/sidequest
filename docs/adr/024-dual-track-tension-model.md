# ADR-024: Dual-Track Tension Model

> Ported from sq-2. Language-agnostic pacing mechanic.

## Status
Accepted

## Context
Drama needs a measurable signal that drives all output systems (narration depth, voice intensity, render priority, delivery mode).

## Decision
`TensionTracker` produces `drama_weight` (0.0-1.0) from two independent tracks plus discrete event spikes.

### Track 1: Gambler's Ramp
Quiet turns accumulate monotony. The longer nothing happens, the higher the tension (because something *should* happen).

| Quiet Turns | Weight |
|-------------|--------|
| 0-2 | 0.0 |
| 3-5 | 0.2-0.4 |
| 6-8 | 0.5-0.7 |
| 9+ | 0.8-1.0 |

### Track 2: HP Stakes
Character health creates mechanical tension.

| HP % | Weight |
|------|--------|
| > 75% | 0.0 |
| 50-75% | 0.3 |
| 25-50% | 0.6 |
| < 25% | 0.9 |

### Event Spikes
Discrete combat moments (critical hit, kill, spell, near-miss) spike tension with decay.

### Combination
```rust
let drama_weight = gambler_ramp.max(hp_stakes).max(event_spike);
```
Uses `max()` to honor any high-tension source.

### Consumers
- **Narration length:** Higher weight = more detailed prose
- **Voice synthesis:** Higher weight = more dramatic delivery
- **Render priority:** Higher weight = more likely to generate image
- **Delivery mode:** < 0.3 instant, 0.3-0.7 sentence-by-sentence, > 0.7 streaming

## Consequences
- Central pacing signal available to all subsystems
- Two tracks handle both narrative monotony and mechanical danger
- Zero LLM cost — pure state comparison and arithmetic
