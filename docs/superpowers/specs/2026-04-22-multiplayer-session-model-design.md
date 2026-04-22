# Multiplayer Session Model — Design

**Date:** 2026-04-22
**Status:** Design approved, pending implementation plan
**Supersedes:** Phase 1 "multiplayer deferred" placeholders in `sidequest-server/sidequest/server/{rest,websocket,session_handler}.py`

## Problem

The current server cannot reliably tell when players come and go, which makes auto-detecting "is this solo or multiplayer right now?" unworkable. Sessions go stale, mode inference is wrong, and the UX breaks in the ambiguous middle. The fix is to stop inferring mode and make it an explicit, frozen choice at game creation.

We also need a coherent story for state synchronization across machines, because each player has a local save file and asymmetric-information rules mean each player's view of the world is legitimately different from the others'.

## Core Model

**A game is a slug.** There is no host role, no lobby owner, no admin. The slug *is* the game.

Slugs are auto-generated at creation:

```
<YYYY-MM-DD>-<world-slug>
```

e.g. `2026-04-22-moldharrow-keep`.

**Same-day + same-world = resume, not new.** If the slug already exists, the selector routes to the existing game without prompting. The user "meant to" — no disambiguation dialog, no "continue or new?" friction.

**Mode is picked explicitly at world select and frozen at creation.** The player chooses `solo` or `multiplayer` before the slug is minted. The choice is written into the game row and cannot be changed later. URL namespace reflects mode:

- `/solo/2026-04-22-moldharrow-keep`
- `/play/2026-04-22-moldharrow-keep`

If you want the other mode, pick a different world or a different day. This is intentional — the alternative (inferring mode from presence) is what's currently broken.

**1:1 identity mapping.** One slug maps to exactly one SQLite save file on the narrator-host, and to exactly one unified-narrator Claude resume-session ID (see ADR-066, ADR-067).

## Identity and Joining

**Identity = display name + cookie.** No accounts, no auth, no seat tokens. First visit prompts for a name; it's stored in `localStorage` and attached to every WebSocket connect frame. Server trusts it. Spoofing is a non-concern for the playgroup this game is built for (see `CLAUDE.md` — trusted gaming group, not public service).

**Joining a multiplayer game:** anyone with the URL can connect at any time — before the game starts, during active play, after a long idle. There is no "lobby owner" to approve joins. A mid-game arrival whose display name is already bound to a seat on this slug resumes that character; a new name runs chargen and claims a fresh seat. There is no separate spectator mode — if you're on the slug, you have a seat.

**Seat claim = soft binding, not identity.** Arriving with a display name already bound to a seat on this slug resumes that character. Arriving with a new name runs chargen and claims a fresh seat. The `(slug, display_name) → character` association is a claim, not an invariant: seats can be vacated, characters can die or retire, and a name can re-chargen into a new seat. The claim mechanism is already specified — see `PLAYER_SEAT` with `character_slot` in Plan 03 Task 3, and the `PlayerState`-in-`SharedGameSession` model in ADR-037. The exact vacate / retire / re-chargen UX is a follow-up; the data model supports it.

**No "start the server" ceremony.** The first visitor to a slug that does not yet exist triggers creation: world select → mode pick → save file + Claude session allocated. Subsequent visitors simply connect. Whoever's machine happens to be running `sidequest-server` is the narrator-host for that slug (see "Narrator-Host" below).

**Solo mode is single-slot and hard-rejects second connections.** A `/solo/...` URL accepts exactly one active connection. A second browser opening the same URL is turned away — no spectator fallback, no read-only downgrade. If multi-viewer access is wanted, the game must be started in multiplayer mode from the start (pick a different world or a different day). The important invariant: solo is not "multiplayer with one player," it's a different mode with different UX (no turn waits, no sealed letters, no party slots, no filtered projections).

**Drop-out = pause.** If anyone in the current party disconnects mid-game, the narrator does not advance. No timeout-based kick, no nudge UX, no auto-skip. The game waits until they reconnect. This matches Sunday-session reality and respects Alex's pacing needs (see `CLAUDE.md` primary audience).

## State and Synchronization

**Single writer, many filtered readers.**

### Narrator-host

One machine per slug is the **narrator-host**: the machine that booted the slug first and holds the Claude resume-session ID. The narrator-host is:

- sole write authority for world, narrative, NPC, encounter, and dice-resolution state;
- canonical holder of `~/.sidequest/saves/<slug>.db`;
- the only node that talks to Claude for narrator calls.

There is no election protocol in this spec. The narrator-host is implicitly "whichever machine is up." Discovery from the player's side is web-URL based: peers reach the game via a URL that resolves to whatever machine is currently serving, with no LAN discovery ceremony or "which machine is up?" prompt. The hosting-side specifics of that URL resolution (tunnel, shared hostname, LAN fallback) belong to a follow-up deployment spec.

### Peer saves are per-player projections, not replicas

Each peer holds its own `<slug>.db` on disk, but it is **not a copy of the canonical save**. It is a projection of the canonical state through that player's asymmetric-information filter:

- what that character has witnessed;
- what's in that player's private inventory / notes / secrets;
- GM reveals targeted at that specific player;
- party-wide information once shared.

Two peers' save files are both legitimate and deliberately different. The canonical save on the narrator-host is the union; each peer save is a projection.

### Write path

All writes go through the narrator-host over the existing WebSocket. Peers submit action intents (move, speak, roll, edit-sheet); the narrator-host validates, mutates canonical state, persists, then fans out **filtered event deltas** per-player.

There is **no peer-authoritative state slice.** Peers do not write locally and sync up. This eliminates merge conflicts, CRDT complexity, and the class of bugs where two peers diverge.

### Read path and reconnect

Peer save = durable log of the filtered event stream that peer has received, plus a derived snapshot for fast UI boot.

On reconnect, peer sends `last_seen_seq`; narrator-host streams missed events (still filtered per-player). When the narrator-host is *down*, peers can open their local save read-only — character sheet browsable, past narration readable, but no advancement possible.

### Filtering

The per-player filter on outbound events is a dedicated layer on the narrator-host. Its architecture is already specified across three existing documents:

- **ADR-028 (Perception Rewriter)** — per-player narration rewrites driven by character status effects (Charmed, Blinded, Deafened, Frightened, Invisible). Canonical narration is preserved on the server; rewrites are produced per-recipient and run concurrently (`tokio::join!`), so total latency is the slowest single rewrite, not accumulated.
- **ADR-037 (Shared-World / Per-Player State)** — the `TargetedMessage { target_player_id: Option<PlayerId> }` envelope is the visibility-tagging model: `None` = fan-out, `Some` = unicast. Region co-location via `resolve_region()` determines whether two players share narration context at all.
- **Plan 03 (`mp-03-filtered-sync-and-projections.md`)** — the wire-level scaffolding: `EventLog` with monotonic `seq`, `ProjectionFilter` protocol returning `FilterDecision { include, payload_json }`, per-player IndexedDB cache, and `last_seen_seq` reconnect replay. Plan 03 ships a `PassThroughFilter` as the default — concrete rules drop into the same interface without re-wiring.

In this spec's terms: the narrator-host appends every mutation to the EventLog, Perception Rewriter produces per-recipient narration variants where character state diverges, and ProjectionFilter is the final include/redact/omit gate per recipient before the socket send. Concrete filter-rule catalog (what each player is entitled to see at each beat beyond the status-effect rewrites) remains follow-up work, but the scaffolding it plugs into is fixed, not TBD.

## Non-Goals

This spec deliberately does not solve:

- **Presence/staleness heuristics.** The explicit mode choice plus pause-on-drop makes this unnecessary.
- **Narrator-host election or failover.** Assumed single stable node per slug; discovery is web-URL based. Deployment/reachability is a separate spec.
- **Peer-authoritative state, CRDTs, conflict resolution.** No peer writes → no conflicts.
- **Seat-vacate / retire / re-chargen UX.** Seat-claim data model is defined (ADR-037, Plan 03 Task 3); the UX for dissolving a seat is follow-up.
- **Multi-viewer solo.** No spectator fallback on `/solo/...`. Start a multiplayer game if more than one person needs to see it.
- **Auth, accounts, anti-spoof.** Display-name + cookie is sufficient for the target audience.
- **Mode-change paths.** No solo→MP or MP→solo conversion. Create a new slug instead.

## Open Follow-Ups (Flagged, Not Blocking)

- **Filter-rule catalog** — concrete rules beyond the ADR-028 status-effect rewrites (e.g. private-inventory reveals, whispered GM notes, perception-check gating) that slot into the `ProjectionFilter` interface from Plan 03. The *interface* is fixed; the *rules* are follow-up.
- **Seat-vacate / retire / re-chargen UX** — the data model in ADR-037 and Plan 03 supports seat dissolution; the user-facing flow (how a player retires a character, how a seat is marked vacant, how a name is allowed to re-chargen) is follow-up.
- **Narrator-host deployment/reachability** — web-URL discovery is the answer from the player's side, but the hosting-side specifics (tunnel, shared hostname, LAN fallback) belong to a separate deployment spec.

## Impact on Existing Code

Current placeholders to reconcile:

- `sidequest-server/sidequest/server/rest.py` — `GET /api/sessions` currently returns empty with a "Phase 1: always empty" comment. Becomes the slug-aware listing endpoint.
- `sidequest-server/sidequest/server/websocket.py` — header comment "no dice dispatch, no shared session sync, no multiplayer." Shared-session fan-out is in scope for this spec.
- `sidequest-server/sidequest/server/session_handler.py` — `_build_session_start_party_status` already exists at line 1174; extend for multiplayer party composition rather than reinvent.

Persistence path (`~/.sidequest/saves/<slug>.db`) keyed by slug is consistent with existing `CLAUDE.md` guidance.
