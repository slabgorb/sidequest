# 13-10

## Problem

**Problem:** Three silent failure modes in the multiplayer turn system allowed players to get stuck, disappear, or play with corrupted character state — all without any error message to the player or any log entry for the team to investigate. **Why it matters:** In a multiplayer game session, a player whose disconnect isn't fully cleaned up becomes a "ghost" — other players can't take their turn because the system is still waiting for someone who left. A player whose character data silently corrupts loads into a broken state with no way to know why.

---

## What Changed

Think of the server as a doorman managing a round-table game. Three things were broken:

1. **The turn sign-up sheet was being ignored.** When a new player tried to join the turn rotation, the server was throwing away any "sorry, you can't join" response. Now it reads that response — and tells the player immediately if something went wrong, so they're not waiting for a turn that will never come.

2. **The cleanup crew would give up if the door was busy.** When a player disconnected, the server tried to wipe their name off the board — but if anyone else was using the board at that exact moment, it would just shrug and walk away. That player's name stayed on the board forever (a "ghost player"), blocking everyone else's turns. Now the cleanup crew waits its turn and always finishes the job.

3. **Character data failures were producing blank entries.** When loading a saved character, the game could fail to package up the character's stats — and instead of stopping or warning anyone, it would just stuff an empty slot into the character sheet. Now it logs the failure and, where appropriate, tells the player to reconnect.

---

## Why This Approach

The root cause in all three cases was the same engineering pattern: **silently discarding errors** using idioms that say "try this, and if it fails, do nothing." That pattern is appropriate when failure truly doesn't matter — but in a multiplayer session coordinator, every one of these failures cascades into a broken game state.

The fix replaces each of those silent-discard patterns with explicit handling: check the result, log what went wrong, and either recover gracefully or surface the error to the player. The disconnect race condition required an additional structural fix — changing from a "try to grab the lock right now or give up" strategy to a "wait for the lock and then finish" strategy. This is the correct behavior for cleanup code, which must complete reliably even under load.

---
