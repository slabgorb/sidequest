# Narrative

## Problem Statement
**Problem:** The game's magic system was running invisibly — when a character's magical abilities loaded up at the start of a scene, the GM dashboard showed nothing. The event fired, but it went nowhere useful. **Why it matters:** The GM panel is the project's lie-detector — it exists specifically so a human observer can verify the game engine is actually doing what the narration claims. If magic initialization is silent, there's no way to confirm the system engaged rather than Claude just improvising spell descriptions from thin air. Two new events (`wwn.magic_hydrated`, `magic.state_hydrated`) were orphaned: they existed in the engine but were invisible to the structured monitoring tab where they needed to appear.

---

## What Changed
Think of the GM dashboard like an airplane cockpit. There are two displays: a raw "everything" readout (the equivalent of a scrolling log) and a clean, organized "Subsystems" panel where each major system — combat, spells, movement — gets its own labeled row. Previously, magic initialization events appeared only on the raw readout, in an unlabeled, unformatted stream. This story wires those two events into the Subsystems panel so they appear in the right row, with the right label, alongside every other magic event. No new features were added; existing invisible signals were made visible in the right place.

---

## Why This Approach
There were two ways to fix this. Option A: stamp new labels directly onto the raw events and teach the UI to recognize them. Option B: route the events through the same pipeline every other magic signal already uses — a shared "translation layer" that handles formatting, labeling, and display routing automatically.

The team chose Option B. The analogy: Option A is like writing a custom adapter for every new appliance you buy. Option B is like installing a standard outlet — future magic events just plug in. Because the existing pipeline already handles `wwn.spell.cast` and `wwn.effort.commit` correctly, routing the two new events through the same path means they inherit correct behavior for free, and the pattern is self-documenting for the next engineer.

---
