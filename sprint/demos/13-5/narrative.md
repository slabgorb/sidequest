# 13-5

## Problem

**Problem:** Players had no way to know which turn mode the game was in — Free Play, Structured, or Cinematic — without guessing from context clues. **Why it matters:** Each mode changes how the game works: in Free Play you act immediately; in Structured everyone submits before anything happens; in Cinematic the AI narrator is in control. Playing the wrong mode by accident wastes time and breaks immersion.

---

## What Changed

A small badge now appears in the game interface that always shows which mode you're in — **Free Play** (green), **Structured** (blue), or **Cinematic** (purple). Hover over it and a one-sentence explanation pops up telling you exactly what that mode means in plain English. When the game shifts from one mode to another, the badge briefly animates to catch your eye so you don't miss the change.

---

## Why This Approach

The badge reuses the game's existing mode type system — it doesn't define its own idea of what a "mode" is. That means it can never get out of sync with the actual game engine. The tooltip text was written to be player-readable, not developer-readable: "Actions resolve immediately" rather than "async turn resolution disabled." The animation-on-change behavior was kept minimal: a flash to draw attention, not a full transition that would distract during active play.

---
