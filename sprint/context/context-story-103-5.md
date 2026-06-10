---
parent: context-epic-103.md
workflow: tdd
---

# Story 103-5: World core (GM lane) — world.yaml + lore.yaml + history.yaml

## Business Context

The world's spine: the files that make `seaboard_of_saints` a loadable, selectable (eventually) world and give the narrator its cosmological ground truth — the Glory plague as the Annunciation, the Shake software-cascade, New Catholicism, and the Magisterium's Plenary-Council governance. Every other content story (regions, cultures, factions, Saints flavor) hangs off the doctrinal frame established here. 103-6 and 103-7 are blocked on this story.

## Technical Guardrails

- **Files:** `worlds/seaboard_of_saints/world.yaml`, `lore.yaml`, `history.yaml` — follow flickering_reach's structure as the convention template (it's the only sibling world in this genre).
- **`draft: true` in world.yaml** until the 103-9 asset gate is MET — keeps the world out of selection (the staging tree was retired 2026-06-03; draft flag is the mechanism).
- **Tone targets (world spec §2):** literary-gonzo, comic dystopia where life works fine — *the Seaboard is not a wasteland; cities work.* NOT survival, NOT tacky-gonzo, NOT monoculture. The "Works." register per region is doctrine.
- **Cosmology fidelity (spec §4):** the five readings of the Glory (Magisterium / Whitman Circle / Brahmin remnant / Lo'in / Sleepers' Sodality) and the Wild-Mutant doctrine (un-marked not heretical; year's catechumenate; Saint Florica precedent) are load-bearing for faction politics — carry them into lore.yaml structured enough for narrator retrieval (ADR-118 indexes lore).
- **No mechanics promises:** AWN Plans 3–7 aren't live — lore must not narratively promise radiation tracks, survival mechanics, or enclave sims (the generalized "double-truth" risk from the AWN spec).
- **Cliché bans (spec §11)** apply to every invented name; real place names (Sleepy Hollow) keep their names.

## Scope Boundaries

**In scope:**
- world.yaml (axis snapshot, description, starting location, `draft: true`)
- lore.yaml (the Glory, the Shake, New Catholicism, Magisterium incl. Wild-Mutant marking doctrine, the five tradition readings)
- history.yaml (pre-war → Glory → fifteen centuries of corridor history; the canonical real-history anchors: Ursuline burning 1834, Anti-Rent War 1839-45, Bread-and-Roses 1912, etc.)

**Out of scope:**
- Regions/places/cartography (103-6), cultures/factions (103-7), saints flavor (103-4), tropes/openings (103-8)
- Any asset references (103-9) beyond placeholders the loader tolerates

## AC Context

1. **Loads clean:** server loads the world with these three files + the 103-1 skeletal saints.yaml; `draft: true` keeps it out of world selection. Test: world-load integration + selection-list assertion.
2. **Cosmology coverage:** lore.yaml contains the Glory-as-Annunciation frame, all five tradition readings, and the Wild-Mutant doctrine, in retrievable units (ADR-118 floor-and-fill can surface them). 
3. **Tone compliance:** no survival framing, no wasteland-despair register, no banned coinages; spot-check by cliche-judge in 103-10.
4. **Starting location** set to a Corridor city consistent with 103-6's planned region set (recommend Providence — Athenaeum + Federal Hill density; final call is the author's, recorded here).

## Assumptions

- Can start immediately (no dependency on 103-1 beyond coexisting in the same world dir; the skeletal world.yaml from 103-1's proof content merges into this story's full version — coordinate if both are in flight).
- flickering_reach's file conventions are current (verified 2026-06-10: world/lore/history/cartography/cultures/legends layout).
