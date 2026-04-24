---
id: 49
title: "Narrator Verbosity and Vocabulary (Two-Axis Text Tuning)"
status: accepted
date: 2026-04-01
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [narrator]
implementation-status: live
implementation-pointer: null
---

# ADR-049: Narrator Verbosity and Vocabulary (Two-Axis Text Tuning)

> Retrospective — documents a decision already implemented in the codebase.

## Context
Narration style requirements vary sharply across player contexts: a solo player deep in an immersive RPG session wants long, literary prose; a multiplayer group at a table needs tighter narration that doesn't stall group pacing; a younger or accessibility-focused player may prefer simpler diction regardless of length preference.

A single "narration detail" slider conflates two independent axes — how much text versus what kind of text. Conflating them forces a choice: literary but brief, or verbose but plain. Players want orthogonal control.

## Decision
Narration style is controlled by two independent enums transmitted in the WebSocket CONNECT payload and stored per-session:

- `NarratorVerbosity`: `Concise | Standard | Verbose` — controls response length/density
- `NarratorVocabulary`: `Accessible | Literary | Epic` — controls diction complexity and register

A player can combine any verbosity with any vocabulary (e.g., `Verbose + Accessible` for long but plain text, `Concise + Epic` for punchy high-register prose).

Both enums implement `default_for_player_count(n: usize)`:
- Solo (n=1): `Verbose / Literary`
- Multiplayer (n>1): `Standard / Literary`

At prompt construction time, both are injected into the Late attention zone as named sections, per ADR-009's principle that format instructions benefit from high recency:

```
[NARRATION LENGTH]
Verbose: write full descriptive paragraphs. Do not truncate scene-setting or emotional beats.

[NARRATION VOCABULARY]
Literary: use elevated but accessible prose. Prefer concrete imagery over abstraction.
```

The UI exposes both as sliders (`VerbositySlider.tsx`, `VocabularySlider.tsx`) that emit updated values over the live WebSocket connection, taking effect on the next narration call.

## Alternatives Considered

**Single verbosity slider** — rejected: conflates length with complexity. A player wanting brief but flowery prose has no way to express that. The two axes are genuinely independent.

**Genre-fixed defaults with no player control** — rejected: genre sets the world tone but not the player's preferred reading density. A player running `space_opera` at a crowded table needs `Concise` regardless of genre defaults.

**Free-text style instructions from the player** — rejected: inconsistent results. "Write like Cormac McCarthy" produces different output across Claude versions. Named enum values map to stable prompt text that can be tuned and tested independently.

**Per-agent style injection** — rejected: each agent (narrator, creature_smith, ensemble) would need to independently honor style settings. Centralizing in the orchestrator's prompt builder guarantees consistency.

## Consequences

**Positive:**
- Players get meaningful control over narration feel without exposing prompt engineering.
- Orthogonal axes prevent the false tradeoff between length and register.
- `default_for_player_count()` makes the defaults sensible out of the box without configuration.
- Late-zone injection means style instructions are near-top-of-mind for the model at generation time.

**Negative:**
- Two sliders in the UI add surface area to the settings panel. Players who don't understand the distinction may find it confusing.
- Nine distinct combinations (3×3) need to be validated for prompt quality. Not all combinations have been playtested equally.
- Mid-session slider changes take effect immediately, which can create jarring style discontinuities mid-scene if changed carelessly.
