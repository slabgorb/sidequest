# Narrative

## Problem Statement
**Problem:** Nine stories of foundational work — Saints, Stocks, mutations, regions, factions, content — had been built in parallel, but no single test had verified the whole chain worked together from "create a character" to "finish a fight." Additionally, the new Saint machinery introduced a risk of contaminating *flickering_reach*, an existing mutant_wasteland world that was specifically designed to stay Saint-free. **Why it matters:** A system that passes all its unit tests but breaks end-to-end is a system that fails at the table. If Saint drawbacks don't fire mechanically when they should, or if a player character's stock trait silently does nothing in a confrontation, the game lies to the player. The OTEL spans (`awn.saint.applied`, `awn.stock.applied`) exist precisely so this isn't taken on faith — they are the proof-of-work receipt that the engine actually engaged the new mechanics, not Claude improvising around them.

---

## What Changed
The final story of the Seaboard of Saints epic wired up a comprehensive end-to-end harness that exercises every system built over the preceding nine stories in sequence:

1. **Character creation** — a player picks a Stock (say, an Animal-strain mutant) and a Saint (a religious archetype that bundles specific mutations). The test walks this path in full, verifying the chargen state machine transitions cleanly.

2. **Narrator opening** — the game session launches, and the first narrator beat is verified to reflect the character's stock and Saint affiliation in its framing.

3. **Confrontation with mechanical proof** — the character enters a fight where their Saint's drawback *must* trigger (the test picks a Saint with a known confrontation-relevant penalty). The OTEL span `awn.saint.applied` fires with the correct mutation ID payload — the engine didn't just narrate around it, it applied it.

4. **Save cycle** — the session saves and reloads cleanly, with no data loss for stock or Saint state.

5. **flickering_reach regression lock** — a separate test loads the *flickering_reach* world and asserts zero Saint content: no `saints.yaml` bindings resolve, no `awn.saint.applied` spans fire. This world is Wild-mutant only, and the test enforces that the Saint machinery's world-tier scoping doesn't bleed across.

6. **Cliché-judge audit** — the shipped content (regions, factions, archetypes, NPC names, trope flavors) was passed through the cliché-judge, and flagged phrases were revised before the story closed.

---

## Why This Approach
The OTEL-assertion pattern (require a specific span to have fired before calling the test a pass) is the project's standard lie-detector for AI-driven systems. Because the narrator is a large language model, it can produce convincing prose that *sounds* like a Saint drawback fired without the engine having done anything mechanical. The only way to know the difference is a trace: did `awn.saint.applied` appear in the watcher log, with the right mutation ID attached? If yes, the mechanic ran. If no, the game lied. By making the integration tests assert on spans rather than on narration text, the test suite becomes immune to the narrator's improvisational talent.

The flickering_reach regression test exists because the Saint system was intentionally built as a world-tier opt-in. Without a test that asserts it *doesn't* appear in opt-out worlds, any future change to the Saint machinery could silently infect worlds that want nothing to do with it. Adding an explicit zero-content assertion now catches that class of bug forever.

The cliché-judge pass is the last quality gate before the world is considered shippable. It runs after all content is in place, so it catches compound patterns that emerge from the full set together — a faction name that seemed fine in isolation but rhymes badly with a region name introduced three stories later.

---

## Before/After
| | Before (103-1 through 103-8) | After (103-10) |
|---|---|---|
| **Integration confidence** | Each story tested in isolation; no proof the full chain worked | Single end-to-end test drives chargen → confrontation → save per stock |
| **Saint drawback firing** | Assumed to fire based on unit tests; narrator could mask silence | `awn.saint.applied` span asserted in the watcher trace — receipt required |
| **Stock trait in confrontation** | Applied at chargen, no downstream verification | `awn.stock.applied` span fires at the confrontation seam and is asserted |
| **flickering_reach isolation** | No explicit protection; Saint plumbing could silently leak | Zero-span assertion: any future bleed fails the regression test immediately |
| **Content cliché state** | Unknown — 9 stories of parallel content had never been audited together | Full cliché-judge pass complete; flagged phrases revised before ship |
| **World status** | Engine complete, no proof it held together | Integration tests green, world ready for asset gate (103-9) |
