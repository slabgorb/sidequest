---
id: 119
title: "Authenticated Player Identity — Player-vs-Character Identity Split via Cloudflare Access"
status: accepted
date: 2026-05-31
deciders: ["Keith Avery", "Major Margaret Houlihan (Architect)"]
supersedes: []
superseded-by: null
related: [37, 67, 104, 105, 108]
tags: [multiplayer]
implementation-status: partial
implementation-pointer: "docs/superpowers/specs/2026-05-31-67-6-player-identity-design.md"
---

# ADR-119: Authenticated Player Identity

> **Sits under ADR-037 (shared-world / per-player state split).** This record
> separates three concepts that were collapsed into one field: `player_id`
> (per-socket key), `player_identity` (authenticated human), and
> **character perspective** (the seated PC's POV key).

## Status
Accepted

## Context

Player display identity was derived from a user-typed `payload.player_name`,
which in the multiplayer flow **is the character name** — the UI sends the
character name as `player_name`. So `_SessionData.player_name` was overloaded
as both the *display identity* and the *seated-character POV key*. This is why
`party_location(perspective=sd.player_name)` accidentally worked, and why
`PARTY_STATUS` fabricated peer identity as `pname = char.core.name`, producing
the doubled "X — X" header (67-4 patched the symptom in the UI without fixing
the root).

The app sits behind Cloudflare Zero Trust (`app.py`), which injects
`Cf-Access-Authenticated-User-Email` on every request — including WebSocket
upgrades — but this header was never read.

Wiring the email into `sd.player_name` blind would break perception/location
POV, because that field is read as a character-perspective key at multiple
call-sites. The fix is to **separate the three concepts** currently tangled
into two fields.

## Decision

Separate three concepts:

| Concept | Meaning | Source of truth | Home |
|---|---|---|---|
| `player_id` | per-socket key (unchanged) | UUID minted at connect | `sd.player_id`, room |
| **player_identity** | the human — authenticated email | `Cf-Access-Authenticated-User-Email` → `Host` → raise | `SessionRoom._player_identities` (room-only, ephemeral) |
| **character perspective** | the seated PC's name — the POV key | `snapshot.player_seats[player_id]` | snapshot (already persisted) |

**Resolution order** (per `player_identity.py`):
1. `Cf-Access-Authenticated-User-Email` header (case-insensitive; blank/whitespace
   treated as absent).
2. `Host` header — local-dev players distinguish themselves via per-player
   hostnames (`player1.local`, `player2.local`) mapped in `/etc/hosts`; the
   port suffix is stripped.
3. **Raise `MissingPlayerIdentityError`** — no typed-name fallback, no silent
   default (No Silent Fallbacks).

**Identity is ephemeral.** It lives in `SessionRoom._player_identities` keyed
by `player_id`, populated on every connect, and dropped on disconnect. It is
never written to the Postgres save (no PII in saves, no staleness).

**Character perspective** is accessed through a single greppable accessor
`perspective_character_name(sd)` (`snapshot.player_seats[sd.player_id]`) that
replaces every site that was passing `sd.player_name` as a `perspective=`
argument. Behaviorally identical today — both equal the character name — but
semantically correct and immune to the identity field changing underneath.

**`sd.player_name`** is retained as the seated-character name it already is.
No rename or retirement this story (blast radius exceeds one story; deferred).

**PARTY_STATUS** (`build_session_start_party_status` in views.py) stops
fabricating peer `pname = char.core.name`. Each party entry carries two fields:
- `character_name` ← `player_seats[player_id]` (always present)
- `player_identity` ← `room._player_identities.get(player_id)` (nullable —
  present for connected players, `None` for seated-but-disconnected)

The UI renders the identity suffix from `player_identity`; when `None`, shows
the character name alone. No fabricated suffix, ever.

**OTEL:** emit a `player_identity_resolved` span on each resolution carrying
`{source: cf_access | host, player_id}` — **not** the email value (PII stays
out of telemetry). The GM panel can confirm whether identity resolved from the
real auth header or a dev Host, satisfying the OTEL Observability Principle.

This ADR sits under the **ADR-037** (shared-world / per-player state split)
umbrella.

## Consequences

- A WebSocket connection with no resolvable identity is closed with a policy
  close-code (1008) and a loud log — misconfiguration, not a guest. Fail-loud.
- Identity is always fresh from the auth boundary; offline (seated-but-
  disconnected) peers show their character name with no identity suffix.
- `sd.player_name` is retained as the seated-character name (no rename this
  story); full rename/retire is deferred.
- Local multiplayer in development requires per-player Host names in
  `/etc/hosts`; a single shared `localhost` cannot distinguish two local players.
- No PII is written to Postgres save files; identity can never go stale.

## Alternatives considered

- **Persisting identity into the snapshot/save** — rejected: PII in saves,
  and the auth boundary is always available on reconnect, making persistence
  redundant.
- **Re-admitting the typed `player_name` as a dev identity source** — rejected:
  re-introduces the conflation that caused the bug; local Host names are a
  cleaner dev-time seam.
- **Full rename/retire of `sd.player_name` to `sd.character_name`** — deferred:
  blast radius (multiple call-sites across session_state, handlers, views)
  exceeds the scope of one story.
- **Reading the header only after chargen** — rejected: the trust boundary
  should be established at the WS accept boundary, not deferred into the game
  flow.
