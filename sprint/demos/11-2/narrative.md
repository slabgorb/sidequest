# 11-2

## Problem

**Problem:** The game engine had no structured way to store or search the lore that gives each world its flavor — legends, faction histories, location descriptions, character backstories. Content was either hardcoded or scattered across YAML files with no runtime querying capability. **Why it matters:** Without a queryable lore layer, the AI narrator can't retrieve contextually relevant world details during a scene, which produces generic, repetitive narration that breaks immersion.

---

## What Changed

Think of LoreStore like a searchable library card catalog that lives entirely in the game server's memory.

Before this story, lore entries existed only as flat files. Now, when the server starts, it loads those entries into a fast in-memory index — organized by **category** (e.g., *locations*, *factions*, *creatures*) and tagged with **keywords**. Two query paths were added:

1. **"Give me everything in category X"** — returns all lore under a named bucket.
2. **"Find entries mentioning keyword Y"** — searches across all categories for relevant content.

No database, no network call. It all lives in RAM and responds in microseconds.

---

## Why This Approach

Three reasons this design was chosen over alternatives like a SQLite database or a full-text search service:

1. **Speed over persistence.** Lore is read-only at runtime — it's authored in YAML and loaded once. There's no need for write durability, so a database would add complexity with no benefit.
2. **Zero dependencies.** An in-memory structure in Rust needs no external service, no Docker container, no connection pool. The game server stays self-contained.
3. **Fits the load pattern.** The narrator queries lore many times per scene but the data never changes mid-session. An indexed hashmap is the textbook solution for this read-heavy, write-once pattern.

---
