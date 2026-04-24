---
id: 23
title: "Session Persistence"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [game-systems]
implementation-status: live
implementation-pointer: null
---

# ADR-023: Session Persistence

> Ported from sq-2. Rust adaptation: rusqlite replaces JSON files (see architecture.md ADR-006).

## Context
Game state must survive server restarts and provide "Previously On..." recaps.

## Decision (Python origin)
- **State:** JSON file (Pydantic model dump), overwritten each save
- **Narrative log:** Append-only JSONL, one event per line
- **Recap:** Generated from narrative log on session resume

### Narrative Log Entry
```json
{"turn": 5, "agent": "narrator", "input": "I enter the cave", "response": "The darkness...", "location": "Dark Cave", "timestamp": "..."}
```

### Rust Adaptation
The Rust port upgrades to SQLite via rusqlite:
- **State table:** Serialized GameState as JSON blob with metadata columns
- **Narrative log table:** Indexed by turn, agent, timestamp
- **Benefits:** Atomic saves, queryable history, single file per save

The "Previously On..." recap generation remains the same — query recent narrative log entries and summarize.

### Auto-Save
State is saved after every turn. Crash recovery loses at most one turn.

## Consequences
- Save files are self-contained (one .db file per save slot)
- Narrative history is queryable for recap generation
- Migration path from Python JSON saves to SQLite is one-time import
