# Spec — `ACTION_REVEAL` Wire Contract Section for `api-contract.md`

**Date:** 2026-05-11
**Status:** Ready for Tech Writer landing
**Author:** Architect (White Queen) — design only; Tech Writer to land
**Driver:** Live Teammate Typing shipped with the wire contract documented only in a superpowers spec (`2026-05-03-live-teammate-typing-design.md`). `docs/api-contract.md` is the load-bearing wire-protocol doc and lists `ACTION_REVEAL` in the message-type table at line 86 but has no detail section. ADR-036 covers the *doctrine* (two amendments, 2026-05-03 + 2026-05-09); this fills the *wire shape* gap.
**Related:** ADR-036 amendments (Action Visibility Model 2026-05-03; Doctrine Clarification 2026-05-09), ADR-051 (round counter authority), spec `docs/superpowers/specs/2026-05-03-live-teammate-typing-design.md`.

## Why No New ADR

ADR-036 is the canonical ADR for multiplayer turn coordination. Its 2026-05-03 amendment names `ACTION_REVEAL` and the four OTEL events; its 2026-05-09 amendment explicitly lists `docs/api-contract.md` as a doctrine doc that must reflect the live wire. A third amendment to spell out the wire shape would push ADR-036 toward becoming a protocol manual. The cleaner home for the wire contract is the file already named *api-contract.md*. Cross-references both directions keep the graph traversable.

## Scope

Drop a new `### ACTION_REVEAL` section into `docs/api-contract.md` under **Server → Client Messages**, and add a sibling entry under **Client → Server Messages** noting that `composing` and `submitted` originate at the client. Sweep two stale references at the same time.

## Drift From The 2026-05-03 Spec (Live Code Wins)

The implemented payload differs from the spec text in two field names. The api-contract section must follow the **live code**, not the spec:

| 2026-05-03 spec | Live wire (verified against `protocol/messages.py:387` and `handlers/action_reveal.py`) |
|---|---|
| `text: string` | **`action: str`** |
| `player_name: string` | **`character_name: NonBlankString`** |
| (not present) | **`player_id: NonBlankString`** on the payload (server-stamped) |
| `seq: number` | `seq: int` (`Field(ge=0)`) |
| `round: number` | `round: int` (`Field(ge=0)`, server-stamped) |
| status enum: `composing|submitted|cleared` | unchanged |
| `aside: boolean` | unchanged |

OTEL events also have one drift to note: `action_reveal.cleared` carries a `reason` field on the *watcher event*, but the wire payload has **no** `reason` field. The four OTEL events are:

- `action_reveal.composing` — fields: `slug`, `player_id`, `round`, `seq`, `text_length`
- `action_reveal.submitted` — fields: `slug`, `player_id`, `round`, `text_length`, `aside`
- `action_reveal.cleared` — fields: `slug`, `player_id`, `round`, `reason` ∈ {`dispatch`, `disconnect`, `timeout`}
- `action_reveal.dropped_rate_limit` — counter; fields: `slug`, `player_id`, `round`

Server-side rate-limit floor is **100ms** per `(socket_id)` for `composing` status only; `submitted` bypasses the floor. Source: `handlers/action_reveal.py:31` — `_COMPOSING_FLOOR_S = 0.100`.

Client-side debounce is **250ms** in `InputBar.tsx` (recommended cadence; not enforced server-side beyond the 100ms floor).

## Drop-In Content For `api-contract.md`

### Insertion point A — Client → Server side (after `### YIELD (outbound)` block ending at line 159, before `### PLAYER_SEAT (outbound)` at line 161)

````markdown
### ACTION_REVEAL (outbound — live teammate typing)
Broadcasts in-progress action text to peers in real time. ADR-036 amendment 2026-05-03 (Action Visibility Model). Clients send `composing` (debounced ~250ms) and `submitted`; the server emits `cleared` and clients sending `cleared` are silently dropped.

```json
{
  "type": "ACTION_REVEAL",
  "payload": {
    "player_id": "",
    "character_name": "Rux",
    "status": "composing",
    "action": "I creep along the rafters",
    "aside": false,
    "seq": 3,
    "round": 0
  },
  "player_id": ""
}
```

- `player_id` and `round` are server-stamped on fan-out — client-supplied values are overwritten (`handlers/action_reveal.py:107-112`).
- `seq` is monotonic per `(player_id, round)`; receivers drop non-monotonic seq within a round. Round transitions hard-flush state.
- `status` ∈ `composing` | `submitted` | `cleared` (`cleared` is server-only).
- `action` is the current text; empty string when `status="cleared"`.
- `aside: true` is the OOC convention; broadcast identically to in-character text.
- Server rate-limit floor: 100ms per socket for `composing` (excess silently dropped, OTEL counter increments). `submitted` bypasses the floor.
````

### Insertion point B — Server → Client side (replace the existing one-line ACTION_QUEUE / CHAPTER_MARKER / ERROR block at lines 413-417, and add a new dedicated section above it)

Add this new section **before** the existing `### ACTION_QUEUE / CHAPTER_MARKER / ERROR` section:

````markdown
### ACTION_REVEAL (inbound — peer fan-out)
Broadcast to all party members except the sender so peers can coordinate during cinematic-mode rounds. ADR-036 amendment 2026-05-03 (Action Visibility Model) — collaborative visibility is the default; the submit-and-wait barrier and CAS dispatcher are unaffected.

```json
{
  "type": "ACTION_REVEAL",
  "payload": {
    "player_id": "alex-123",
    "character_name": "Rux",
    "status": "submitted",
    "action": "I draw my pistol and watch the door.",
    "aside": false,
    "seq": 7,
    "round": 2
  },
  "player_id": "alex-123"
}
```

Lifecycle for one peer across a single round:

1. Peer types first char → `composing` with `seq=0`.
2. Peer keeps typing (250ms client debounce) → `composing` updates with monotonic `seq`.
3. Peer hits send → `submitted` with the final `action`.
4. Server-elected dispatcher fires barrier → server emits `cleared` for every peer (one per player, sequenced after the prior payload).
5. Round `N+1` opens; per-peer `seq` resets to 0; receivers hard-flush state on round transition.

**`cleared` is server-only.** It fires at three sites:
- *Dispatch* — `session_room._emit_action_reveal_cleared` runs at barrier-fire, before the narrator dispatches.
- *Disconnect* — last-socket disconnect emits `cleared` (`reason="disconnect"`) so peers don't see frozen ghost typing.
- *Timeout* — cinematic-mode timeout cleanup (not yet wired; placeholder).

**Privacy.** OTEL watcher events carry `text_length` only, never `action` content. Player input is sensitive; length + cadence + count are sufficient for the GM-panel lie-detector.

| OTEL event | Fields |
|---|---|
| `action_reveal.composing` | `slug`, `player_id`, `round`, `seq`, `text_length` |
| `action_reveal.submitted` | `slug`, `player_id`, `round`, `text_length`, `aside` |
| `action_reveal.cleared` | `slug`, `player_id`, `round`, `reason` ∈ {`dispatch`, `disconnect`, `timeout`} |
| `action_reveal.dropped_rate_limit` | `slug`, `player_id`, `round` (counter) |

See ADR-036 amendments (2026-05-03 + 2026-05-09) for the doctrine and the three-meaning disambiguation of "sealed-letter".
````

### Sweep item — stale lifecycle text at lines 459-467

The current `## Session Lifecycle` block at line 459 reads:

```
6. Multiplayer turn flow (STRUCTURED mode):
   - All players submit PLAYER_ACTION independently
   - Server holds actions until SessionRoom.TurnBarrier resolves (all
     submitted or timeout — adaptive per active turn-takers, story 45-2)
   - One handler claims and calls narrator with combined action; others
     receive broadcast
   - Server sends TURN_STATUS per player as they submit; ACTION_REVEAL when
     the seal opens
   - Shared-world delta (location, encounter id, party adjacency) flows
     between turns via the shared-world handshake (story 45-1)
```

Two issues:

1. **`STRUCTURED mode`** is wrong — the live mode is **Cinematic** per ADR-036's 2026-04-26 implementation notes (Structured is dead code).
2. **`ACTION_REVEAL when the seal opens`** is wrong — `ACTION_REVEAL` fires *continuously during the wait window* (collaborative visibility per the 2026-05-03 amendment), not only at seal-open.

Replace with:

```
6. Multiplayer turn flow (Cinematic mode — the live default):
   - All players submit PLAYER_ACTION independently
   - Server holds actions until SessionRoom.TurnBarrier resolves (all
     submitted; timeout default deferred — story 45-2 closed the active-
     turn-takers vs lobby-count gap)
   - During the wait window, ACTION_REVEAL fans out continuously so peers
     see each other's in-progress and post-submit text (ADR-036 amendment
     2026-05-03; collaborative visibility is the default). Server stamps
     player_id + round; clients debounce composing updates at ~250ms.
   - One handler wins the CAS guard and calls narrator with the merged
     party action; others receive the broadcast.
   - At barrier-fire, server emits ACTION_REVEAL with status=cleared for
     every player before dispatching the narrator.
   - Server sends TURN_STATUS per player as they submit.
   - Shared-world delta (location, encounter id, party adjacency) flows
     between turns via the shared-world handshake (story 45-1).
```

### Sweep item — header date

Bump `**Last updated:** 2026-05-05` → `**Last updated:** 2026-05-11`.

### Sweep item — message-type table at line 86

The existing one-line entry is fine — leave as is:

```
ACTION_REVEAL         Peer action-text reveal (multiplayer; collaborative visibility per ADR-036 amendment 2026-05-03)
```

(No change needed; verify it still reads correctly after the section additions.)

## What Mock Turtle Should NOT Touch

- ADR-036 itself — the two amendments already say what they need to.
- The 2026-05-03 superpowers spec — preserved as historical design context; the live wire is the source of truth.
- `feature-inventory.md` — already updated 2026-05-11; the live-teammate-typing row points to ADR-036 and the spec, which is correct.

## Verification Checklist (Mock Turtle, before exit)

- [ ] `### ACTION_REVEAL (outbound …)` lands under "Client → Server Messages" between YIELD and PLAYER_SEAT.
- [ ] `### ACTION_REVEAL (inbound …)` lands under "Server → Client Messages" above `### ACTION_QUEUE / CHAPTER_MARKER / ERROR`.
- [ ] Field names match live code: `action` (not `text`), `character_name` (not `player_name`), `player_id` on the payload.
- [ ] `STRUCTURED mode` swept to `Cinematic mode` in the Session Lifecycle block.
- [ ] `ACTION_REVEAL when the seal opens` line replaced with the continuous-broadcast text.
- [ ] Header `Last updated` bumped to 2026-05-11.
- [ ] Two cross-references back to ADR-036 amendments (2026-05-03 + 2026-05-09) present.
- [ ] No mention of a hypothetical ADR-099. ADR-036 is the home of this doctrine.

## Out Of Scope

- Documenting the dogfight `sealed_letter.py` cross-product table — that's a different system, already linked from ADR-077.
- Sealed visibility (PvP) mode — not implemented; deferred per ADR-036's 2026-05-09 amendment.
- Wire-level docs for `PLAYER_ACTION`, `PARTY_STATUS`, `TURN_STATUS`, `ACTION_QUEUE` — already documented elsewhere in api-contract.md; this spec is `ACTION_REVEAL`-only.
