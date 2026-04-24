---
id: 26
title: "Client-Side State Mirror"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [frontend-protocol]
implementation-status: live
implementation-pointer: null
---

# ADR-026: Client-Side State Mirror

> Ported from sq-2. Defines server-side requirements for the API contract.

## Decision
The React client maintains a local read-only GameState mirror. The server piggybacks state deltas on narration messages so the client stays in sync without polling.

### Server Responsibility
Every `NARRATION` and `TURN_STATUS` message includes an optional `state_delta` field:

```json
{
  "type": "NARRATION",
  "payload": {
    "text": "The orc lunges...",
    "state_delta": {
      "location": "Dark Cave",
      "characters": [{ "name": "Grok", "hp": 15, "max_hp": 20, "statuses": ["poisoned"] }],
      "quests": { "Find the Gem": "in_progress" }
    }
  }
}
```

### Client Slash Commands
Slash commands (`/inventory`, `/map`, `/status`) resolve from the local cache with zero server round-trip. The server never needs to handle these.

### Sync Guarantee
WebSocket is reliable-ordered, so deltas arrive in order. Full state sync occurs only on disconnect/reconnect via `SESSION_EVENT { event: "ready", initial_state: {...} }`.

## Consequences
- Server must compute and include state deltas with every narration
- Slash commands are purely client-side (zero server cost)
- Reconnect sends full state snapshot
