# Narrative

## Problem Statement
Problem: The UI codebase contained two unused code artifacts — a deprecated `OverlayType` enum with no active consumers, and calls to a `groupPortraitSegments` function that had been quietly doing nothing for some time. Why it matters: Dead code accumulates like clutter in a workshop. It slows down engineers trying to understand the system, creates false leads during debugging, and adds surface area that future changes must navigate around. Every hour a developer spends wondering "is this thing used somewhere?" is an hour not spent on real features.

---

## What Changed
Two pieces of unused code were removed from the game's front-end:

1. **OverlayType** — a label system for visual overlays that was defined but never actually referenced anywhere in the application. Like a light switch with no lights attached to it.

2. **groupPortraitSegments** — a function that was being called in several places but had no effect. Imagine a button wired to nothing; this removed both the button and the dead wire.

No user-visible behavior changed. The app looks and works exactly the same. The improvement is entirely internal — a cleaner, more trustworthy codebase.

---

## Why This Approach
When code has zero consumers, the safest and most honest fix is deletion. Keeping it "just in case" sends a false signal to future engineers that it matters. Removing it is low-risk (nothing breaks since nothing used it) and high-value (the codebase now says only true things). This kind of hygiene work is the equivalent of taking out the trash before it becomes a problem — unglamorous but essential.

---
