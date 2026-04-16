# 37-7

## Problem

Problem: The "Back" button during character creation was broken — clicking it did nothing, leaving players stuck. Why it matters: Character creation is the very first thing a new player does. A non-functional back button on the first screen they interact with signals a buggy product and forces players to refresh the browser, losing any progress they'd made.

---

## What Changed

When a player clicks "Back" during character creation, the app sends a signal to the game server saying "go back." The server wasn't set up to understand that signal — it didn't recognize "back" as a valid action, so it silently ignored it. The fix taught the server to accept the back signal and respond correctly, returning the player to the previous step.

---

## Why This Approach

The UI and server had drifted out of sync — the front end was doing its job correctly, but the back end's rulebook didn't include the "back" action. Rather than working around this with client-side tricks, we fixed it at the source: updated the server's accepted action list so both sides speak the same language. Clean, permanent, no hacks.

---
