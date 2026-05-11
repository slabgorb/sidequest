# 39-9

## Problem

Problem: In the caverns_and_claudes dungeon-crawl pack, the Constitution stat (CON — a character's physical endurance and toughness) appeared in only 3 out of 35 possible challenge types, despite this being a game about exploring dark, dangerous underground environments where exhaustion, bad air, and filthy water should be constant threats. A dungeon delver with CON 17 played identically to one with CON 9 for 91% of the descent. Why it matters: this breaks the fundamental promise of character building — the choices players make during character creation should feel meaningful during play. Sebastien, the group's mechanics-focused player, will notice this immediately. The mismatch also surfaced a housekeeping issue: the game's display schema was still advertising HP, armor class, and hit point fields that were intentionally removed from the game over a year ago.

---

## What Changed

Think of the game's challenge library like a menu at a restaurant. Before this change, the "endurance" section of the menu had only three dishes — but the kitchen was fully equipped to make twenty. This story added five new CON-gated challenges to the library:

- **Cave-Air Poisoning** — bad gas pockets in deep tunnels; tough characters push through, fragile ones get woozy
- **Forced March Fatigue** — relentless pace breaks down weaker bodies
- **Holding Breath** — submerged passages, flooded corridors
- **Cold Soak** — wading through freezing underground streams
- **Bad Water Dysentery** — drinking from contaminated pools mid-descent

On top of that, 2–3 existing challenges that were ambiguously labeled "needs strength *or* endurance" were cleaned up and formally assigned to CON ownership. No more coin-flipping by the narrator.

Finally, three display fields — HP, Max HP, and Armor Class — were removed from the game's stat display configuration. These fields were deleted from the game engine over a year ago per a deliberate design decision (the game uses Momentum, Edge, and Fate instead), but their labels were still showing up in the schema like a ghost employee on the payroll.

---

## Why This Approach

The fix was kept entirely in content files — no server code was touched. This was the right call because the problem was a gap in the data, not a bug in the engine. The engine already knew how to evaluate CON checks; it just had almost nothing to evaluate. Adding new beat types to the YAML vocabulary is low-risk, immediately testable, and doesn't require a deployment cycle. It also means any future content contributor can add more CON beats the same way, without touching Python or needing a code review.

The stat display cleanup is a similar story: the game's rules schema is authoritative for what the UI shows. Removing dead fields from the schema is safer than patching around them, and it prevents the narrator from accidentally referencing stats the game no longer tracks.

---
