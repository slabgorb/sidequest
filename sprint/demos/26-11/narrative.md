# 26-11

## Problem

Problem: When players disconnected and reconnected to an active game session, the game lost track of where each character was located — causing some players to appear in the wrong place, or in a different location than their party members, with no way to reconcile the gap.

Why it matters: Session reconnection is a routine part of any live game — network hiccups, browser refreshes, device switches. If reconnecting breaks the party's shared sense of place, the game becomes unplayable. Players see different scenes, the GM loses authoritative state, and the narrative falls apart mid-session.

---

## What Changed

Think of the game session like a shared map on a table. When everyone's sitting together, the map is obvious. But if someone steps away and comes back, the game now knows how to hand them an updated copy of exactly where everyone is — including players who may have moved to a different area while they were gone.

Previously, the reconnect handshake only restored the reconnecting player's *last known* position. Now it performs a full reconciliation: it checks where every party member currently is, identifies any divergence, and syncs all locations to a consistent shared state before resuming play.

---

## Why This Approach

Location state is the single source of truth for what scene the player is experiencing. Rather than trying to patch over disagreements after the fact, the fix resolves divergence at the reconnect moment — the only clean seam in the session lifecycle where a full sync can happen without disrupting active gameplay. Doing it earlier (mid-scene) would cause visual jumps; doing it later means the player is already receiving wrong content.

---
