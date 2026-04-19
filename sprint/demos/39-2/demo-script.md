# Demo Script — 39-2

**Total runtime: ~8 minutes**

**Slide 1 — Title (30 sec)**
Introduce the story: "Today we're talking about one of those invisible-but-critical cleanup stories — removing a concept from the game engine's foundation that never should have been there."

**Slide 2 — Problem (90 sec)**
Walk through the before state. Show the old `CreatureCore` struct with `hp`, `max_hp`, and `ac` fields. Ask the audience: "If you're a developer reading this, what do you think HP means in a SideQuest combat?" Pause. "That's the problem. It looks like it means something. It doesn't."

*Fallback: If live terminal isn't available, show the screenshot of the old struct on Slide 2.*

**Slide 3 — What We Built (2 min)**
Live terminal: navigate to `sidequest-game/src/` and show that `hp.rs` is gone.
```bash
ls sidequest-api/crates/sidequest-game/src/
```
Show the new `Combatant` trait — specifically the `edge()`, `max_edge()`, and `is_broken()` methods. Point out: "Three methods replaced three fields. Same surface area, correct concept."

*Fallback: Show the before/after slide (Slide 5).*

**Slide 4 — Why This Approach (90 sec)**
Reference the compile-error cascade: "When we deleted HP, the compiler told us exactly where HP was being used across all 12 crates. We fixed every single one before merging. No deferred debt."

Show the diff stat: files changed, lines removed. Frame it as subtraction as progress — "we shipped negative lines of code and the game is more correct."

**Slide 5 — Before/After (1 min)**
Walk through the comparison table. Emphasize the `is_broken` flag: "In Edge-based combat, you don't die — you're *broken*, taken out of the scene. That's a design distinction the old HP model couldn't express at all."

**Roadmap slide (1 min)**
Connect to upcoming Edge tuning and the combat balance pass.

**Questions (remaining time)**

---
