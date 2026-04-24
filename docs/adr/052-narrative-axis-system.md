---
id: 52
title: "Narrative Axis System (/tone Command)"
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

# ADR-052: Narrative Axis System (/tone Command)

> Retrospective — documents a decision already implemented in the codebase.

## Context
Genre packs span a wide tonal range within their setting. A pulp noir session might start
hardboiled and shift toward melancholy; a low fantasy adventure might be grim or hopeful
depending on player preference. Locking tone at genre-pack authoring time produces a
one-size-fits-all voice that doesn't adapt to the table.

The narrator prompt already accepts context modifiers. The question was how to expose
tone control to players in a structured, genre-aware way without requiring code changes
for each new genre or tone variant.

## Decision
Genre packs declare arbitrarily many named narrative axes in YAML. Each axis has two poles
with vocabulary and style modifier text. Named presets bundle multiple axis values for
one-command switching.

```yaml
narrative_axes:
  - name: moral_weight
    pole_a:
      label: Grim
      modifiers: ["bleak imagery", "no easy victories", "consequences linger"]
    pole_b:
      label: Hopeful
      modifiers: ["resilience rewarded", "light amid darkness", "earned optimism"]
  - name: pacing
    pole_a:
      label: Terse
      modifiers: ["short sentences", "clipped dialogue", "economy of language"]
    pole_b:
      label: Lush
      modifiers: ["rich description", "sensory detail", "deliberate pacing"]

presets:
  grimdark:
    moral_weight: -0.9
    pacing: 0.2
  pulpy:
    moral_weight: 0.6
    pacing: -0.7
```

Players shift tone mid-session via `/tone set <axis> <value>` or `/tone preset <name>`.
The `/tone` command is a `CommandHandler` implementation wired into `SlashRouter`.

Axis values are stored in `GameSnapshot` as `Vec<AxisValue>` and persist across sessions.
At narrator prompt construction time, active axis modifiers are injected as context, shaping
the LLM's vocabulary and thematic framing without altering the plot or mechanical state.

Implemented in `sidequest-game/src/axis.rs`.

## Alternatives Considered

- **Hardcoded tone modes** — rejected because tone vocabulary is genre-specific. A "grim"
  mode for space opera has different language than "grim" for pulp noir. Hardcoding requires
  code changes per genre.

- **Free-text tone instructions** — rejected because player-typed instructions are inconsistent
  and can conflict with genre pack voice guidelines. Structured axes constrain the space to
  what the genre author intended.

- **LLM-inferred tone from player behavior** — rejected because players cannot observe or
  control what the LLM infers. Explicit axis control gives players reliable agency over the
  narrative voice.

- **Conflating with NarratorVerbosity/Vocabulary (ADR-049)** — rejected because those settings
  control output length and diction formality, not thematic tone. A terse narrator can be
  either grim or hopeful; these dimensions are orthogonal.

## Consequences

**Positive:**
- Genre authors can define axes without any code changes — fully data-driven.
- Players have explicit, observable control over narrative tone with immediate feedback.
- Presets reduce friction for common configurations ("just make it grimdark").
- Axis values persist in `GameSnapshot`, so tone shifts survive session saves.
- Axes compose — a player can set three axes independently to dial in a specific voice.

**Negative:**
- Genre packs that don't define axes offer no `/tone` capability — the command exists but
  has nothing to operate on.
- Axis modifier injection increases prompt token cost slightly on every narrator call.
- Preset definitions can drift from axis scale conventions if genre authors aren't careful
  (e.g., using 0–1 range when the axis expects -1 to +1).
