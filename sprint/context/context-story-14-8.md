---
parent: context-epic-14.md
---

# Story 14-8: Sound Slider Labels

## Business Context

Audio sliders exist but aren't labeled. Players don't know which slider controls what.

**Playtest evidence:** "The sound sliders are not labeled."

## Technical Approach

Pure UI fix. Find the audio settings component in sidequest-ui, add visible text labels
to each slider (e.g., "Master", "Music", "SFX", "Voice", "Ambient"). Labels should be
permanently visible, not tooltip-on-hover.

Check the current slider component to determine what channels exist and match labels
accordingly.

## Scope Boundaries

**In scope:**
- Add text labels to all audio sliders
- Labels visible without hover

**Out of scope:**
- Audio mixing changes
- New audio channels
- Volume presets

## Acceptance Criteria

| AC | Detail |
|----|--------|
| All labeled | Every audio slider has a visible text label |
| No hover needed | Labels are always visible, not tooltip-only |
| Correct names | Labels match the actual audio channel each slider controls |
