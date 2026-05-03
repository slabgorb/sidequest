# Live Teammate Typing — Design Spec

**Date:** 2026-05-03
**Status:** Brainstormed, awaiting plan
**Driver:** Playtest 2026-05-03 — playgroup reported coordination broke down because the cinematic-mode sealed-letter buffer hides too much information from teammates while they plan and submit actions.
**Related:** ADR-036 (Multiplayer Turn Coordination), ADR-037 (Shared-World / Per-Player State Split), ADR-051 (Two-Tier Turn Counter), playtest feedback memory `project_playtest_2026_05_03.md`.

## Problem

In cinematic mode (current default), each player types into a private input box. The server holds submitted actions in a per-room buffer until the barrier fires; nobody sees anyone else's text until narration lands. Coordination collapses at two distinct moments:

1. **Mid-typing.** A player composing their action can't see what teammates are still composing — no opportunity to adjust mutual plans before either commits.
2. **Post-submit, pre-narration.** A fast typist who has already submitted is invisible to a slower typist still composing — the slow typist plans blind.

Both cases came up in the 2026-05-03 playtest. Both are the same underlying problem: the sealed-letter discipline (designed to prevent fast-typist monopolies and protect Alex-pacing) is over-applied as a default and starves the group of coordination signal.

## Goal

Make all teammate action input visible to all party members in real time during cinematic-mode rounds. Preserve the sealed-letter barrier and CAS-guarded dispatcher (those are turn-execution mechanics, untouched). Move information-hiding entirely into narration output (SECRET_NOTE, per-player visibility tags), where it already lives.

## Non-Goals

- Removing or weakening the cinematic-mode barrier. Action *resolution* still happens simultaneously; only *visibility of input* changes.
- The dogfight `sealed_letter.py` cross-product confrontation mechanic. That is a different system that overloads the same name; it is untouched.
- Per-scene or per-player private-input flag. Future scenes may want hidden input (perception rewriter, traitor briefings) but no current playgroup scenario needs it. Defer.
- Reviving FreePlay or Structured modes; cinematic remains the default.
- Journal/lore changes (the *other* playtest finding) — separate spec.

## Principles Applied

- **SOUL — Living World, Yes And:** Coordination *between players* is signal the world should permit; players have always coordinated at a tabletop and the digital medium was inadvertently strangling it.
- **Tabletop First, Then Better:** A tabletop DM doesn't hide what one player is *thinking about saying*; players have body language, half-spoken sentences, and table talk. This feature restores the equivalent.
- **Cost Scales with Drama:** A few-byte WS message every 250ms during typing is cheap; the dramatic value is direct.
- **Wire Up What Exists:** `ACTION_REVEAL` message type and `ActionRevealEntry` payload are stubbed in the protocol. Wire them.
- **Right-Size Ceremony:** No new ADR; amend ADR-036 with a visibility-model section.

## Decisions (from brainstorm)

- **Visibility:** Both mid-typing and post-submit, pre-narration. Always visible across the party. Secrets live in narration output, not input.
- **Granularity:** Client debounces broadcasts to ~250ms.
- **Region scope:** Party-wide regardless of ADR-037 region split. Defer co-location filtering until split-party play actually happens.
- **Aside flag (`aside: bool` OOC):** Broadcast identically. Asides *are* coordination metadata; that's the whole point.
- **No feature flag.** Cinematic mode just becomes more visible. Per CLAUDE.md, no backward-compat shims when changing the code is sufficient.

## Wire Protocol

Single message type — `ACTION_REVEAL` — with a status field discriminating live updates from final reveal from server-driven cleanup.

```ts
ACTION_REVEAL {
  player_id: string;            // who's composing
  player_name: string;          // display name (server authoritative)
  status: "composing" | "submitted" | "cleared";
  text: string;                 // current text; empty when status="cleared"
  aside: boolean;               // OOC aside flag; broadcast identically to IC
  seq: number;                  // monotonic per (player_id, round); receivers drop stale-or-out-of-order
  round: number;                // ADR-051 round counter; receivers ignore prior-round entries
}
```

Lifecycle for one peer across a single round:

1. Peer types first char → `composing` text="I", seq=0.
2. Peer keeps typing, debounced 250ms → `composing` updates, seq=1, 2, 3...
3. Peer hits send → `submitted` with final text, seq=N+1.
4. Server-elected dispatcher fires barrier → `cleared` (server-emitted) for every peer, seq=N+2.
5. Round N+1 opens; per-peer seq resets to 0.

`seq` and `round` exist because stale-read bounces are a known headache here (memory `feedback_pingpong_parallel_writers.md`). Receivers drop messages with non-monotonic seq within a round and hard-flush state across round transitions even if a `cleared` is lost.

## Server Architecture

### New handler

`sidequest/handlers/action_reveal.py` — parallel to `player_action.py`. Accepts only `composing` and `submitted` from clients. Server-emits-only `cleared` (clients sending `cleared` are silently dropped).

- Reuses `SessionRoom.broadcast(msg, exclude_socket_id=sender_socket)` so the typist doesn't see their own echo.
- Server stamps `round` field with its authoritative round counter before fan-out; client-supplied round is ignored.
- Rate-limit safety net: messages from the same `(player_id, round)` arriving faster than ~100ms apart are silently dropped, with an OTEL counter increment.

### `cleared` emission — three trigger sites

1. **Dispatch fires.** In `player_action.py` at the barrier-fired branch (around line 267 per recon), after the elected dispatcher takes the CAS guard, server emits `cleared` for every party member before dispatching the narrator. Clean slate going into narration.
2. **Player disconnect.** Existing socket-disconnect path emits `cleared` (reason="disconnect") for the departed player so peers don't see a frozen "Bob is composing…" with no Bob.
3. **Cinematic-mode timeout default action.** Timeout cleanup emits `cleared` (reason="timeout") for the timed-out player before the default action enters the buffer.

### What is NOT changed

- The cinematic-mode action buffer.
- The barrier / CAS-guarded dispatcher in `player_action.py`.
- `PLAYER_ACTION` message format and handling.
- Any pause-gate behaviour for absent seated players.

This feature is purely additive: a new message type, a new handler, three hook points for `cleared`.

## OTEL Watcher Events

Per CLAUDE.md observability mandate. Emitted from the new handler and the cleared-trigger sites:

| Event | Fields |
|-------|--------|
| `action_reveal.composing` | `player_id`, `round`, `seq`, `text_length` (length only — never content) |
| `action_reveal.submitted` | `player_id`, `round`, `text_length`, `aside` |
| `action_reveal.cleared` | `player_id`, `round`, `reason` ∈ {"dispatch", "disconnect", "timeout"} |
| `action_reveal.dropped_rate_limit` | counter |

Privacy: text content is never written to OTEL, only length. Player input is sensitive; lie-detection works fine on length + cadence + count without leaking text.

## UI Architecture

### `InputBar.tsx` — debounced broadcast

The component already owns `useState<string>` for typed text. Add:

- A 250ms-debounced callback firing `sendActionReveal({status: "composing", text, seq: seq++})` via the existing WS hook.
- On `onSend(text, aside)`: send `{status: "submitted", text, aside, seq: seq++}` *before* dispatching the existing `PLAYER_ACTION`, so peers see the locked text fractionally before narration kicks off.
- Local seq resets to 0 when the round-counter prop transitions.
- Self-echo filter on the receive side: incoming `ACTION_REVEAL` with `player_id === selfId` is dropped (server already excludes via socket id; client filter is belt-and-suspenders for disconnect/reconnect windows).

### New `usePeerReveals` hook

Owns the peer reveal map:

```ts
type PeerReveal = {
  player_id: string;
  player_name: string;
  status: "composing" | "submitted";
  text: string;
  aside: boolean;
  seq: number;
  round: number;
};

// Map<player_id, PeerReveal>
```

- Drop self.
- Upsert on `composing`/`submitted` only when `seq > existing.seq` for that `(player_id, round)`.
- On `cleared`: delete that player's entry.
- On round-counter transition: flush the entire map (failsafe for dropped `cleared`).

### `MultiplayerTurnBanner.tsx` — render the reveals

Today the banner renders one of three states ("free", "waiting-on-peers", "waiting-on-narrator"). Becomes:

```
┌─ Alex is composing ────────────────────────────────────┐
│ I creep along the rafters and try to see what's in—    │
└────────────────────────────────────────────────────────┘
┌─ Bob ✓ submitted ──────────────────────────────────────┐
│ I draw my pistol and watch the door.                   │
└────────────────────────────────────────────────────────┘
─── Waiting on the narrator… ────────────────────────────
```

- One row per peer in `peerReveals`, ordered by party-member order (stable, not by recency — rows don't dance around as people type).
- `composing`: muted left-border colour, header reads "Alex is composing", text shown verbatim.
- `submitted`: solid left-border with ✓, header reads "Alex ✓ submitted", text in slightly dimmed colour.
- `aside`: italicized or `*`-prefixed text — same convention used elsewhere in the UI for OOC.
- Empty `peerReveals` → falls back to the existing default banner. No regression.
- Row enter/exit transitions guarded by `prefers-reduced-motion`. Per Alex-pacing-design-principle: nothing twitchy.

## Edge Cases

| Case | Behaviour |
|------|-----------|
| Fast typer / slow typer | Fast typist sees slow typist's text grow in real time during the wait. *Cannot change own submission* — barrier still locks — but is no longer staring at a blank screen. Direct fix for the playtest finding. |
| Disconnect mid-typing | Socket-disconnect path emits `cleared` (reason="disconnect"). Peers' rows vanish. Existing pause-gate logic takes over. No frozen ghosts. |
| Cinematic-mode timeout | Timeout cleanup emits `cleared` (reason="timeout") before default action enters the buffer. |
| Late-joining peer | Joins with empty map; no backfill of in-flight typing. Acceptable — sees subsequent `composing`/`submitted` updates and `cleared` flush at next dispatch. |
| Out-of-order WS delivery | `seq` discriminator drops stale messages; `round` discriminator hard-cuts on round transitions. |
| Submit-WS in flight | Brief gap where peers see "composing" with the final text before the badge flips to "submitted". Resolves in ~1 RTT. Visually invisible — text content is identical. |

## Out of Scope (parked)

- Concurrent-edit replay / history scrubbing.
- Client-side draft persistence (typist crashes mid-compose).
- Per-player or per-scene private-input mode.
- Mobile / small-screen banner overflow.
- Anti-abuse beyond the server rate-limit safety net.
- Audio cue on peer typing (TTS pipeline removed; not on the table).

## Testing Strategy

### Server (`sidequest-server/tests/`)

- `tests/handlers/test_action_reveal.py` — composing/submitted accepted; client-sent `cleared` dropped; out-of-order seq dropped; rate limit; round stamping.
- `tests/server/test_session_room_action_reveal.py` — fan-out excludes sender; all other party members receive.
- `tests/handlers/test_player_action_clears_reveals.py` — dispatch, disconnect, and timeout each emit `cleared` with the correct reason.
- `tests/server/test_action_reveal_wired.py` — **wiring test** per CLAUDE.md. Real `SessionRoom`, two seated players; sending `composing` from socket 1 produces a broadcast on socket 2 (and not socket 1). Proves the handler is registered in dispatch, not just that the module imports.
- `tests/telemetry/test_action_reveal_otel.py` — full composing → submitted → cleared cycle emits the four watcher events with expected fields. GM panel lie-detector check.

### Client (`sidequest-ui/src/__tests__/`)

- `usePeerReveals.test.tsx` — upsert, monotonic seq, self-filter, cleared, round flush.
- `MultiplayerTurnBanner.test.tsx` — empty fallback, composing row, submitted row, aside, stable order, reduce-motion.
- `InputBar.test.tsx` (new assertions on existing file) — 250ms debounce, submitted fires before PLAYER_ACTION, seq increments and resets.
- `__tests__/action-reveal-wiring.test.tsx` — **wiring test** per CLAUDE.md. Mount `<App>`, mocked WS captures outbound messages; typing produces `composing` outbound; injected inbound `ACTION_REVEAL` renders in the banner. End-to-end through the real component graph.

### Cross-process integration

- Optional `scripts/playtest/scenarios/action-reveal-smoke.yaml` — two-client playtest; OTEL stream shows expected sequence end-to-end. Add only if Keith wants in-process verification before shipping.

### Explicitly NOT testing

- Visual snapshots of the banner (brittle).
- Performance under 8+ simultaneous typers (party size ≤ 6 in practice).

## Verification in Playtest 5

Three pre-session smoke checks (<60s, Keith at the keyboard):

1. `just up` → two browser tabs as separate players → type in tab 1 → confirm text appears in tab 2's banner within ~300ms.
2. Send from tab 1 → confirm tab 2 sees the row flip to "✓ submitted".
3. Submit from both → narration kicks off → confirm both banners flush back to baseline.

If any of those fail, the feature is broken before the playgroup logs in.

## ADR Work

Amend ADR-036 (Multiplayer Turn Coordination) with a new "Action Visibility Model" section: action text broadcasts live to all party members; sealed-letter discipline retreats to *narration output* (SECRET_NOTE, per-player visibility tags). Cross-link from ADR-036 → playtest 2026-05-03 feedback memory and this spec.

No new ADR. No feature flag.

## Risks

| Risk | Mitigation |
|------|-----------|
| WS traffic at scale | 250ms client debounce + 100ms server floor; party size ≤ 6 in practice |
| Stale-read bounce | seq + round discriminators; round transition hard-flush |
| Players feel surveilled | Always-visible was the deliberate user call; no current playgroup scenario needs hidden input; future opt-out is per-scene if it ever matters |
| Distraction during typing | Stable peer ordering (not recency); reduce-motion guards; row layout already tight |

## Implementation Order Hint

For the planning phase: the protocol message + server handler + wiring test land first, before any client work. Once a wiring test proves end-to-end fan-out, the client side is straightforward UI glue and the OTEL coverage drops in alongside. The cleared-trigger hooks in `player_action.py` are the only edits to *existing* server logic; everything else is new files.
