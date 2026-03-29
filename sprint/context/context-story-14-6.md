---
parent: context-epic-14.md
---

# Story 14-6: Image Pacing Throttle

## Business Context

Images are fantastic but come too fast during rapid turn sequences. Players get overwhelmed
and some images arrive for scenes that have already passed. A cooldown prevents flooding
while preserving the impact of each image.

**Playtest evidence:** "The images are coming a little too much, a little too fast, even
though they're fantastic and everybody really enjoys them."

## Technical Approach

### Server-Side Cooldown

Add to `SharedGameSession`:

```rust
pub struct ImageThrottle {
    pub cooldown_seconds: u64,     // configurable
    pub last_image_at: Option<Instant>,
}

impl ImageThrottle {
    pub fn should_generate(&self) -> bool {
        match self.last_image_at {
            None => true,
            Some(last) => last.elapsed().as_secs() >= self.cooldown_seconds,
        }
    }

    pub fn record_generation(&mut self) {
        self.last_image_at = Some(Instant::now());
    }
}
```

### Defaults

| Mode | Cooldown |
|------|----------|
| Multiplayer | 60 seconds |
| Solo | 30 seconds |

### Integration Point

In the image generation trigger path (where the server decides to send an art prompt to
the daemon), check `image_throttle.should_generate()`. If false, skip the image.

### DM Override

DM can force an image at any time via DM tools (bypasses cooldown). The forced image
resets the cooldown timer.

### Configurable

Cooldown is per-session, changeable via session settings. Same SessionSettings message
as verbosity/vocabulary.

## Scope Boundaries

**In scope:**
- ImageThrottle struct with cooldown logic
- Integration into image generation path
- Smart defaults (solo vs multiplayer)
- DM force-image bypass
- Session settings control

**Out of scope:**
- Image queue (suppressed images are dropped, not queued)
- Per-player image preferences
- Image quality/resolution settings

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Throttle works | Second image request within cooldown is suppressed |
| Default differs | Multiplayer 60s, solo 30s |
| DM override | DM can force an image, resetting cooldown |
| Configurable | Cooldown adjustable via session settings |
| First image | First image of session always generates (no initial cooldown) |
