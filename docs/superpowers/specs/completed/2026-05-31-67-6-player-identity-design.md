# 67-6 — Authenticated Player Identity (player-vs-character identity split)

**Date:** 2026-05-31
**Story:** 67-6 (epic 67 — Multiplayer resilience & presence)
**Repo:** sidequest-server
**Workflow:** tdd
**Umbrella ADR:** ADR-037 (shared-world / per-player state split). New ADR to be authored: **ADR-119** — "Authenticated player identity via Cloudflare Access + player-vs-character identity split".

## Problem

Player display identity is derived from a user-typed payload (`payload.player_name`), which in the multiplayer flow **is the character name** — the UI sends the character name as `player_name`. So `_SessionData.player_name` (session_state.py:188) is overloaded: it is simultaneously the *display identity* and the *seated-character POV key*. This is why `party_location(perspective=sd.player_name)` (websocket_session_handler.py:2570) accidentally works, and why PARTY_STATUS fabricates peer identity as `pname = char.core.name` (views.py:606-607), producing the doubled "X — X" header that 67-4 only patched at the UI layer.

The app already sits behind Cloudflare Zero Trust (app.py:305 — "Cloudflare Zero Trust gates access at the tunnel"), so an authenticated identity is available in the `Cf-Access-Authenticated-User-Email` request header — but it is **never read**. `player_identity.py` and its 8 pinning tests existed transiently in 67-4 and were reset; they are recreated here under TDD.

Wiring the email into `sd.player_name` blind would break perception/location POV, because that field is read as a character-perspective key at multiple sites. The fix is to **separate the three concepts** that are currently tangled into two fields.

## Design decisions (settled during brainstorming)

1. **Local-dev identity → per-player Host names.** Resolution order is `Cf-Access-Authenticated-User-Email` (non-blank, case-insensitive) → `Host` header (local dev uses distinct hostnames, e.g. `player1.local` / `player2.local`, mapped in `/etc/hosts`) → **raise**. No typed-name fallback; no silent default. This keeps the contract clean and honors *No Silent Fallbacks*.
2. **Identity storage → room-only, ephemeral.** The resolved identity lives in the live `SessionRoom`, keyed by `player_id`, and is re-resolved from headers on every connect. The auth boundary (Cloudflare) remains the source of truth; identity can never go stale, and **no email/PII is written to Postgres save files**.
3. **Cleanup scope → seam + repoint, keep the field.** Add the `player_identity` lane and a single explicit character-perspective accessor; repoint display/identity consumers to identity and perspective consumers to the accessor. `sd.player_name` is left in place as the seated-character name it already is. We do **not** rename/retire it (deferred — larger blast radius than one story).

## Three named concepts

| Concept | Meaning | Source of truth | Home |
|---|---|---|---|
| `player_id` | per-socket key (unchanged) | UUID minted at connect | `sd.player_id`, room |
| **player_identity** | the human — authenticated email | `Cf-Access-Authenticated-User-Email` → `Host` → raise | `SessionRoom.player_identities: dict[player_id, str]` (room-only, ephemeral) |
| **character perspective** | the seated PC's name — the POV key | `snapshot.player_seats[player_id]` (already exists) | snapshot (already persisted) |

`sd.player_name` already equals the seated character name; it is unchanged. The fix stops *reading* it where identity is meant.

## Components

### New module: `sidequest/server/player_identity.py`

Recreated per the 67-4 contract:

```python
def resolve_player_identity(headers: Mapping[str, str]) -> str: ...
class MissingPlayerIdentityError(Exception): ...
```

- Reads `Cf-Access-Authenticated-User-Email` case-insensitively; a blank/whitespace value is treated as absent and falls through.
- Falls through to the `Host` header (local-dev derivation).
- Raises `MissingPlayerIdentityError` when neither yields a non-blank value.

### New seam accessor: character perspective

A single greppable accessor so the POV key is never an ambient field read:

```python
def perspective_character_name(sd) -> str:
    # returns snapshot.player_seats[sd.player_id]; same empty-string behavior
    # as today's player_seats.get(player_id, "") when no seat is bound yet.
```

### Cross-socket identity store

`SessionRoom` gains `player_identities: dict[player_id, str]`, populated on connect and dropped on disconnect.

## Data flow

1. **WS endpoint** (where `websocket.accept()` happens) reads `websocket.headers`, calls `resolve_player_identity(headers)`. On `MissingPlayerIdentityError` → close the socket with a policy close-code + loud log. A connection with no resolvable identity is a misconfiguration, not a guest (fail-loud).
2. The resolved identity is threaded down the connect path alongside `player_id` into `_handle_connect`.
3. The slug-connect branch stores `room.player_identities[player_id] = identity`.
4. On disconnect, the entry is removed (ephemeral; re-resolved fresh next connect).

**Unchanged lane:** `payload.player_name` still seeds the character / `player_seats[player_id]` exactly as today — chargen, seat-matching, and resume back-fill are untouched. This adds a parallel identity lane; it does not rewire the character lane.

**Perspective repoint:** every site passing `sd.player_name` as a `perspective=` argument (e.g. websocket_session_handler.py:2570) switches to `perspective_character_name(sd)`. Behaviorally identical today (both equal the character name) but semantically correct and immune to the identity field changing underneath it.

## PARTY_STATUS / UI

`build_session_start_party_status` (views.py) stops setting peer `pname = char.core.name`. Each party entry carries **two** fields:

- `character_name` ← `player_seats[player_id]` (always present)
- `player_identity` ← `room.player_identities.get(player_id)` (**nullable** — present for connected players, `None` for seated-but-disconnected)

The UI renders the identity suffix from `player_identity`; when `None`, it shows the character name alone. **No fabricated suffix, ever.** This fixes the doubled "X — X" header at the root, superseding the 67-4 UI guard.

## Error handling

- Missing identity at the WS boundary → close socket + log (No Silent Fallbacks).
- `perspective_character_name` when a `player_id` has no seat yet (pre-chargen) → returns the same empty value today's `player_seats.get(player_id, "")` yields; callers already handle it.

## OTEL

Emit a `player_identity_resolved` span on each resolution carrying `{source: cf_access | host, player_id}` — **not** the email value (PII stays out of telemetry). The GM panel can confirm identity resolved from the real auth header vs. a dev Host, per the OTEL Observability Principle.

## Testing

- **Pinning tests** (recreate the 8 in `tests/server/test_player_identity.py`): header precedence, case-insensitivity, blank-skip, raise-on-none, Host fallback.
- **PARTY_STATUS behavior**: a connected peer carries `player_identity`; a disconnected seated peer carries `None` and no fabricated name.
- **Wiring test (OTEL)**: drive a real connect and assert the `player_identity_resolved` span fired — proves the resolver is reachable from the production WS path, not merely unit-callable (Every Test Suite Needs a Wiring Test).
- **Perspective regression (OTEL/fixture)**: POV/perception still resolves after the `sd.player_name` → `perspective_character_name` repoint.

All wiring assertions use OTEL spans or fixture-driven behavior, never source-text greps (repo rule: No Source-Text Wiring Tests).

## Deliverables

1. **ADR-119** under the ADR-037 umbrella: trust boundary, the three concepts, local-dev Host derivation.
2. `player_identity.py` resolver + `MissingPlayerIdentityError`.
3. WS-boundary header capture + threading into connect; `SessionRoom.player_identities` store.
4. `perspective_character_name` accessor + repoint of `sd.player_name` perspective call-sites.
5. PARTY_STATUS dual-field (`character_name` + nullable `player_identity`); UI suffix sourced from `player_identity`.
6. `player_identity_resolved` OTEL span.
7. Full test suite above.

## Out of scope

- Making `player_id` stable across reconnects (epic-67 presence work).
- Persisting identity into save files.
- Full rename/retire of `sd.player_name`.
- Any change to the character/chargen/seat lane.

## Open assumptions (log as Design Deviation if wrong)

- Local-dev multiplayer uses distinct per-player Host names (`player1.local`, etc.); a single shared `localhost` Host cannot distinguish two local players and would resolve them to the same identity. Dev setup docs must establish the hostnames.
- The FastAPI WebSocket endpoint has `websocket.headers` available before/at `accept()` and can thread values into `_handle_connect`.
- Cloudflare injects `Cf-Access-Authenticated-User-Email` on the WS upgrade request (not only on plain HTTP).
