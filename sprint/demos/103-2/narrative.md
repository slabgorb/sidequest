# Narrative

## Problem Statement
Problem: Players creating characters in the Seaboard of Saints setting had no way to choose a **Stock** — the game's term for species or lineage (human Sleeper, animal-hybrid, and others to come). Without this step, every character started identical, with no inherited traits, biological quirks, or mutation pathways. Why it matters: Stock is the first meaningful identity choice a player makes. It shapes their stats, their mutation options, and how the world reacts to them. Skipping it meant the character creation screen was missing its most evocative moment.

---

## What Changed
Think of Stock like choosing a species at the start of a video game — but with real mechanical teeth. We added a new step in the character creation flow where players pick their Stock. Right now two are available: **Sleeper** (humans who survived the apocalypse via cryo-stasis, carrying implants that strain their system) and one **Animal** (a beast-hybrid lineage).

Each Stock automatically applies its bonuses and penalties — adjustments to strength or speed, armor, trauma resistance — without the player needing to do math. If a Stock grants mutation options, the mutation step that follows now **branches**: Sleepers see one set of choices, Animal stocks see another. The game knows which path to show based on what you picked.

Sleepers also arrive with implants already installed. Those implants aren't free — they cost System Strain (the game's resource for biotech load), so a Sleeper starts slightly more fragile than a blank-slate human, which is true to the fiction.

---

## Why This Approach
We built Stock as a **data file**, not hardcoded logic. Everything about a Stock — its stat changes, movement, armor, trauma target, and which mutations it unlocks — lives in a single `stocks.yaml` file that content authors can edit without touching any engine code. Adding a new Stock (say, a Plant hybrid or a Synthetic) means writing a few lines of YAML, not a pull request to the game engine.

The UI branch at the mutation step works the same way: the game reads the Stock's granted mutation list and shows only the relevant options. No special cases, no if-this-then-that buried in code. The engine is generic; the content drives the experience.

---
