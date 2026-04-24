---
id: 37
title: "Shared-World / Per-Player State Split"
status: accepted
date: 2026-04-01
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [multiplayer]
implementation-status: live
implementation-pointer: null
---

# ADR-037: Shared-World / Per-Player State Split

> Retrospective — documents a decision already implemented in the codebase.

## Context

Multiplayer SideQuest sessions require a clear model for what state is shared across
players (the world) versus what belongs to individual players (the character). Naive
approaches either duplicate world state per player (causing divergence) or merge
everything into one blob (making per-player updates cumbersome).

The existing single-player dispatch pipeline is ~1,950 lines of dense synchronous
game logic. Rewriting it for multiplayer concurrency would be high-risk and slow.
The state model needed to support multiplayer without breaking or rewriting the
single-player dispatch path.

## Decision

World-level game state is stored in a `SharedGameSession` keyed by `genre:world`.
Per-player state lives in `PlayerState` within the shared session. A sync-to-locals /
sync-from-locals pattern checks out world state for dispatch processing and checks it
back in afterward.

**`SharedGameSession`** (`sidequest-server/src/shared_session.rs`, ~340 LOC):

- Keyed by `"genre:world"` — all players in the same world share one session.
- Holds: narration history, NPC registry, trope engine state, music director,
  cartography, and the `HashMap<PlayerId, PlayerState>`.
- Protected by `Arc<RwLock<SharedGameSession>>` — readers can access concurrently,
  writers hold exclusive lock only for state patches.

**`PlayerState`** — nested within the shared session:

- Holds: character sheet, current HP, inventory, active combat state, current region.
- Keyed by `PlayerId` within the session map.

**Sync pattern** in dispatch (`dispatch/mod.rs`):

```rust
// Check out: copy world state + this player's state into a local GameState
let mut local = session.sync_to_locals(player_id)?;

// Run the full single-player dispatch pipeline unchanged
let patches = dispatch_action(&mut local, action).await?;

// Check back in: apply patches to shared session
session.sync_from_locals(player_id, local, patches)?;
```

This preserves the single-player dispatch pipeline verbatim. World state is never held
across async boundaries — the local copy is taken synchronously, dispatch runs, and
patches are committed synchronously before any await point on shared state.

**Fan-out and unicast** use `TargetedMessage` with an optional `target_player_id`.
A `None` target fans out to all players in the session; `Some(id)` unicasts. Both
travel on the same session broadcast channel — no separate connection tracking needed.

**Region co-location** (`resolve_region()`) uses fuzzy name matching to determine
whether two players are in the same area and therefore share narration context. Players
in different regions receive independent narration.

## Alternatives Considered

- **Full CRDT for world state** — rejected. Overkill for a single-server deployment
  where all writes go through one process. CRDTs add merge complexity with no benefit.
- **Separate world process per session** — rejected. Adds inter-process latency on every
  state read; complicates deployment with no gain at current player counts.
- **Per-player world copies** — rejected. State divergence is the core problem CRPGs
  have historically struggled with. Shared state is the correct model; the sync
  pattern is the implementation.
- **Rewriting dispatch for async multiplayer** — rejected. 1,950 lines of correct
  synchronous logic; the sync-to-locals pattern preserves it unchanged.

## Consequences

**Positive:**
- Single-player dispatch pipeline is entirely untouched — no regression risk from
  multiplayer additions.
- World state consistency is guaranteed within a turn: one player's action cannot
  observe another's mid-dispatch patch.
- `TargetedMessage` simplifies the WebSocket layer — one channel handles both broadcast
  and unicast without separate connection registries.
- Region co-location enables correct shared narration for players exploring together
  while still supporting independent play in different areas.

**Negative:**
- The sync-to-locals copy is a full clone of world state; for very large narration
  histories or NPC registries this adds allocation pressure per turn.
- `resolve_region()` fuzzy matching can produce false co-location if region names are
  ambiguous — requires careful content authoring.
- Writers still hold an exclusive lock during `sync_from_locals`; at high player counts
  with simultaneous submissions this creates brief contention windows.
