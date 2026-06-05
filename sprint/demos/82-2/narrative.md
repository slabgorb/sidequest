# Narrative

## Problem Statement
**Problem:** The narrator had two tuning dials — how much it writes (verbosity) and how formal its language sounds (vocabulary) — but players had no way to touch them. The server ignored whatever the player preferred and always narrated at the same fixed setting: "standard" length, "literary" vocabulary. The sliders described in the design document were never built.

**Why it matters:** SideQuest is designed for players with different reading styles. James reads everything; Alex sometimes needs a shorter, plainer version. Jade and Sebastien want to see the crunch, not wade through prose. Locking everyone to the same narrator voice meant the system couldn't serve the table it was built for. The setting dials existed in the engine — they just weren't connected to the player.

---

## What Changed
Think of a podcast app where you can speed up playback or switch between "descriptive" and "brief" summaries — but the knob was always been glued to the same position. This story unstuck the knob.

**What was built:**

1. **Two new controls in the game lobby.** When a player connects, they now see a "Verbosity" selector (Concise / Standard / Verbose) and a "Vocabulary" selector (Accessible / Standard / Literary). The choice is remembered between sessions — open the lobby tomorrow and your preference is still there.

2. **The preference actually rides along to the game.** When the player clicks "Connect," those choices are bundled with the connection message and sent to the server. Previously the server looked at that part of the message and ignored it.

3. **The server now listens.** Instead of hardcoding "standard/literary" every single turn, the game engine reads the player's preference, stores it, and uses it to shape every narrator response for that session.

4. **Returning to a saved game works too.** Load a game from last week, and the server restores the verbosity and vocabulary settings that were active when you saved — they don't reset to a default.

5. **Smart defaults by group size.** A solo player gets "verbose" by default (no one is waiting on them); a multiplayer table defaults to "standard" (keep the pace up). The vocabulary side now follows the same logic — this was previously missing, leaving the two dials mismatched in how they handled defaults.

6. **An observer panel now confirms it's working.** The GM/developer dashboard now shows the active verbosity and vocabulary setting for each turn, with a note on whether it came from the player's choice or from a smart default. This is the "lie detector" — proof the narrator is actually following the setting, not improvising.

---

## Why This Approach
**Closing the loop, not redesigning the system.** The narrator prompt builder already had the wiring — it had functions for verbosity and vocabulary sections that fired every turn. The problem was that those functions were being called with hardcoded "standard/literary" rather than the player's actual preference. This story didn't rebuild anything; it connected the player controls to the pipeline that was already there.

**Validated, not trusted blindly.** When a preference is saved to the browser's local storage and later loaded, it's checked against an allowlist of valid values before being sent to the server. If something garbled or unexpected comes in, it's quietly dropped and the server uses its smart default — loud-when-it-matters, graceful-when-it-doesn't.

**localStorage as the bridge.** The game lobby (where you set preferences) and the actual game connection are two separate parts of the app. Rather than threading state through the entire UI tree, preferences are written to local storage in the lobby and read out when the connection fires — the same pattern the display-name setting already used.

**Tests that break on the current code.** The test suite was written first — before any implementation — specifically to fail on the hardcoded defaults. This means the moment a developer accidentally re-introduces "narrator_verbosity = 'standard'" as a literal anywhere, a test breaks. The pipeline proves itself end-to-end: slider → connection message → server session → turn context → narrator prompt section.

---
