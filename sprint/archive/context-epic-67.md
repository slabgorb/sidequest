# Epic 67: Multiplayer resilience & presence

## Overview

Harden multiplayer turn/socket robustness and shared-turn presence against the failure modes surfaced in Playtest-3. The throughline: **a single client's local failure (a render crash, a dropped socket, a sealed peer) must never orphan the whole table's in-flight turn**, and the shared-turn status the table reads must be one canonical, slow-typist-friendly surface.

**Priority:** P1
**Repo:** server, ui
**Stories:** 4 (14 points)

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **ADR-036** Multiplayer Turn Coordination (`docs/adr/`) | Submit-and-wait turn barrier; 2026-05-03 amendment (peer action text visible during wait); 2026-05-09 doctrine clarification (sealed visibility is PvP-reserved, not built) |
| **ADR-037** Shared-World / Per-Player State Split (`docs/adr/`) | What is table-shared vs per-player; basis for reconnect replay |
| **ADR-023** Session Persistence (`docs/adr/`) | SQLite save substrate; apply→persist seam |
| **ADR-105 / ADR-104** Perception firewall (`docs/adr/`) | Constrains what reconnect-replay may surface to each player |
| Playtest-3 ping-pong findings (source, since archived) | Origin of all four stories |

## Background

SideQuest's playgroup is the load-bearing audience, and multiplayer is how they actually play. Playtest-3 exposed that the multiplayer turn loop is fragile at the *client* edge in ways that punish the *whole table*:

- A client-side **GameBoard React render crash** could tear that client out of the turn loop, and the table's in-flight turn could be lost rather than recovered (→ 67-1).
- **ACTION_REVEAL** delivery wasn't resilient — a sealed peer could stall indefinitely at "Composing" if the reveal didn't arrive (→ 67-2).
- Shared-turn / peer-visibility status was scattered across surfaces, and slow typists (Alex) had no reassurance the table was waiting *with* them, not *on* them (→ 67-3).
- MP identity mapping conflated player and character, rendering doubled `X — X` headers (→ 67-4).

These are resilience and presence bugs, not features. The design bar (CLAUDE.md): never rush a slow typist, never let one player's local problem degrade the shared experience.

**Key existing-infrastructure note (verify, don't reinvent):** recon during 67-1 setup found that much of the resilience substrate already exists — an `ErrorBoundary` wraps GameBoard (`sidequest-ui/src/App.tsx:2019`), the server persists each turn before the client renders it (`websocket_session_handler.py:~4003`), and reconnect already replays per-player filtered events from the event log (`handlers/connect.py:1073-1270`). The epic's job is to **close the gaps** between these pieces and prove the end-to-end path under real failure, not to rebuild them.

## Technical Architecture

**Server (`sidequest-server/sidequest/`)**
- Turn apply→persist seam: `server/websocket_session_handler.py` — `_handle_player_action()` (:3364) → `_execute_narration_turn()` (:3374) → persistence (`_room.save()` / `sd.store.save(snapshot)`, :3996-4044). The invariant the epic protects: **persist happens before/independent of any single client successfully rendering**.
- Multiplayer turn coordination & disconnect: `server/session_room.py` — pending-action buffer (:183-200), `disconnect(socket_id=...)` (:448-571, ref-counted presence so a multi-socket player isn't dropped on one socket close), ADR-036 action-visibility clearing (:551-570).
- Reconnect replay: `handlers/connect.py:1073-1270` — projection-cache replay of per-player filtered events since `last_seen_seq`, with tail-backfill so a reconnecting client always sees at least the last NARRATION block.
- Event log (persisted to SQLite): `game/event_log.py`.

**UI (`sidequest-ui/src/`)**
- `components/GameBoard` wrapped by `ErrorBoundary name="Game"` (`App.tsx:2019`; boundary impl `components/ErrorBoundary.tsx`).
- WebSocket lifecycle: `hooks/useWebSocket.ts` (onclose/reconnect :177-186, detachHandlers :129-135) and `hooks/useGameSocket.ts` (game wrapper, reconnect on non-1000 close).

**Cross-cutting constraint:** any reconnect-replay or presence work must respect the ADR-104/105 perception firewall — a reconnecting or recovering client may only be re-shown what its player was entitled to see. OTEL: every resilience seam touched must emit a watcher event so the GM panel can confirm the fix engaged (CLAUDE.md OTEL principle).

## Cross-Epic Dependencies

**Depends on:**
- ADR-023 session persistence and ADR-036/037 turn-coordination substrate (already live) — the foundation reconnect-replay builds on.

**Depended on by:**
- None within the sprint; the four stories are largely independent, though 67-3 (presence surface) and 67-2 (ACTION_REVEAL resilience) both touch the "Composing/Sealed/Resolving" status the table reads.
