# 16-9

## Problem

**Problem:** SideQuest now supports eight different encounter types — standoffs, chases, fights, negotiations, interrogations, net combat, ship battles, and auctions — but the game UI only knows how to show a combat screen. Every new encounter type the engine understands is invisible to the player; the screen goes blank or falls back to a generic text log.

**Why it matters:** The entire Epic 16 effort to build a genre-flexible encounter engine is wasted player-experience value if there's no visual component to match. A spaghetti western standoff and a cyberpunk netrun should *feel* completely different on screen — different framing, different color language, different tension mechanics — but today they'd look identical. Genre identity lives or dies at the UI layer.

---

## What Changed

Think of it like a single "smart display" that knows how to dress itself for the occasion. Before this story, the game had separate, hand-coded screens for combat and chases. Every other encounter type was unrecognized — the engine knew about it, but the screen didn't.

The new `ConfrontationOverlay` component is one unified screen that inspects what kind of encounter is happening and picks the right visual presentation automatically:

- **Standoffs** (spaghetti western): widescreen letterbox framing, extreme close-up portraits, a rising tension bar in dust-and-gold colors
- **Chases**: hands off to the existing chase visualization with its separation meter and rig stats
- **Combat**: preserves the current battle layout exactly — no visual regression
- **Social encounters** (negotiation, interrogation, trial): leverage or resistance bar, dialogue beat buttons, actor portraits
- **Net combat, ship battles** (future types): the same component will pick up genre theme colors and stat labels from the YAML pack, no code changes needed

The component reads two things from the game state: the confrontation type and the genre theme. Those two signals drive every visual decision — colors, layout framing, label text, and which stats appear.

---

## Why This Approach

The alternative was building a separate overlay component for each encounter type — which is exactly how combat and chase ended up siloed in the first place. That approach creates a maintenance tax where every new genre pack needs a new UI file.

Instead, the component treats visual rules as data, not code. Genre packs already declare confrontation types in YAML with metric names, beat labels, and mood tags (from stories 16-2 through 16-7). The UI component reads those declarations and applies them. Adding a new encounter type to a genre pack doesn't require touching React code — the schema drives the display.

The standoff letterbox framing is the one hard-coded exception: it's a deliberate cinematographic choice tied to the spaghetti western genre identity, not a general rule. Everything else is data-driven.

---
