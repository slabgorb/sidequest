# 39-2

## Problem

**Problem:** The game engine was tracking character health using traditional hit points (HP) — a concept borrowed from classic tabletop RPGs. SideQuest's combat system is built around "Edge" (composure/momentum), not HP, but the code still had HP wired in at the foundation. This meant every creature in the game was carrying dead weight: fields that tracked health in a way the game never actually used.

**Why it matters:** Dead fields don't just waste space — they're landmines. Any developer (or AI agent) touching combat code could read those HP fields and assume they meant something, writing logic against a ghost. The longer the mismatch persisted between the game's *conceptual model* (Edge-based combat) and its *data model* (HP fields), the more likely the engine would drift in the wrong direction.

---

## What Changed

Think of it like renovating a house that was built with gas fixtures, then converted to electric — but someone left all the old gas lines in the walls "just in case." This story rips out the gas lines.

Specifically:
- Every creature in the game used to carry three fields: current HP, max HP, and armor class (AC). Those are now gone.
- In their place: current Edge, max Edge, and a "broken" flag (is this creature out of the fight?).
- A whole file dedicated to HP math (`hp.rs`) was deleted entirely.
- Everywhere in the codebase that touched HP — and it was *everywhere* — was updated to use Edge instead.
- Creatures are now initialized with placeholder Edge values so the system compiles and runs while the real tuning work continues.

---

## Why This Approach

The team chose a hard cutover rather than a gradual migration for a simple reason: gradual migrations on a foundational type create a window where both systems exist simultaneously and neither is trustworthy. When you have `hp` and `edge` fields sitting next to each other on the same struct, every reader has to ask "which one does the game actually use?" The answer is: nobody knows, because both are plausible.

Ripping out HP entirely forces every downstream consumer to confront the new model *now*, while the cascade of compile errors serves as a complete map of every place the old assumption lived. Compile errors are the best possible dependency graph — they don't lie, don't get stale, and can't be ignored.

The placeholder values in constructors are an honest acknowledgment that tuning is future work. They are *not* stubs — the system runs, Edge is tracked, combat resolves. The numbers just need calibration.

---
