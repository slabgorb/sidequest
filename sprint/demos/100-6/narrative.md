# Narrative

## Problem Statement
**Problem:** The game's reference pages — the rule books, power tables, and encounter guides players consult during play — were generated as raw HTML by the server, meaning the server was in the business of both *knowing* the rules AND *drawing the page*. That's two jobs crammed into one place, and it made the pages impossible to modernize without touching the server.

**Why it matters:** The reference pages contain sensitive, game-master-only content (narrator hints, NPC behavior scripts, encounter difficulty tuning) sitting right next to player-facing content. Mixing them in one HTML blob made it impossible to cleanly share the safe content with players while keeping the secret sauce locked away. Every future UI improvement was blocked by this entanglement.

---

## What Changed
Imagine a librarian who used to walk up to every patron, read their book aloud in a whisper, and tear out the secret pages before the patron could see them — every single visit, manually.

We replaced that with a photocopy machine that has a built-in shredder: you ask for the rules for *Space Opera*, the machine reads the master copy, automatically shreds the pages marked "GM only," and hands you a clean packet in a standard format. The server now has one job: produce the clean packet. The browser (soon) has one job: display it.

Concretely:
- A new API endpoint `/reference/api/rules/{pack}` was created on the game server
- It reads the rules YAML files for any genre pack (combat rules, power tables, encounter vocabulary)
- It runs every field through the existing **firewall** (`reference_visibility.py`) — the same security layer used by all the lore pages shipped in stories 100-2 through 100-5
- It returns a clean JSON document; GM-only fields never appear in the output
- One bug was caught and fixed during review: an invisible Unicode character (an em-dash) in the test data was causing the firewall's self-check to pass vacuously — the shredder was reporting "no secret pages found" because it couldn't read the label. That was corrected and re-verified.

---

## Why This Approach
**Reuse the firewall, don't rebuild it.** Stories 100-2 through 100-5 built and battle-tested the `build_generic_yaml_section` projection pipeline — a function that reads any YAML document and strips keeper fields before returning it. Rules files are just YAML. Rather than write a custom scrubber for rules, this story routes rules through the same pipe. The keeper carves for rules (narrator hints, NPC behavior, obstacle stats) were already registered in the firewall from prior work; this story just unlocked the door.

**Pack-scoped, not world-scoped.** Rules belong to a genre pack (`space_opera`, `heavy_metal`), not to an individual world within a pack. The endpoint is `/reference/api/rules/{pack}` — one level up from the lore endpoints, which include a world slug. This matches the data reality and avoids a world-context dependency that doesn't apply here.

**No session required.** Players looking up the rules shouldn't need to be logged into an active game. The endpoint is fully public. The firewall handles all access control by stripping what shouldn't be seen; authentication adds nothing here.

---
