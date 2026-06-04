---
parent: context-epic-77.md
workflow: tdd
---

# Story 77-8: Project the quests spine to the client — emit quest_log + quest_anchors + active_stakes outbound (RELATIONSHIPS-snapshot analog)

> **Provenance.** Created 2026-06-04 as the blocking prerequisite surfaced by TEA
> during 77-5's RED phase. 77-5 (the UI quest/objective panel, `repos: ui`) is parked
> in `backlog` and depends on this story. This standalone context file was recovered
> by TEA from the rich `## Story Context` section sm-setup wrote inline into
> `.session/77-8-session.md` (the known sm-setup standalone-file gap).

## Business Context

The wry_whimsy/oz playtest (2026-06-02) and the gulliver playtest both ran against
worlds whose entire premise *is* a campaign spine — yet the player had **no objective
surface at all**. ADR-137 (quest & stakes substrate) answered that with a server lane
(77-1…77-4) that seeds and maintains a per-session spine — `quest_log`,
`quest_anchors`, `active_stakes` — and a committed UI fast-follow (77-5) to render it.

The server lane landed and is OTEL-verified: the spine is **stored** and **mutated**
correctly. But TEA's 77-5 RED investigation found the spine is **never serialized
outbound to the client**. The render-only UI panel therefore has nothing to consume.
This story closes that gap: it puts the spine on the wire in a typed projection the UI
can mirror, so the player (and especially the mechanics-first players, Sebastien &
Jade, who want campaign state legible in a *player-facing* surface) can finally see
what they're working toward and what's at stake. This is the wire half of that
legibility; 77-5 is the render half.

## Technical Guardrails

- **Mirror the ADR-136 RELATIONSHIPS snapshot pattern — do not invent a new one and
  do not piggyback the thin legacy field.** The reference is
  `sidequest-server/sidequest/server/websocket_handlers/relationships_emit.py`
  (~48-82): a dedicated message type + payload (`RelationshipsMessage` /
  `RelationshipsPayload`), change-gated via an internal signature (no-op on unchanged
  data), invoked from the websocket session handler alongside the other shared-world
  frame emissions (location/tactical/magic). Build the analogous QUESTS projection.
  Do **not** stuff the spine into the legacy `StateDelta.quests: dict[str,str]` field
  (`protocol/models.py:235`) — that field is title→status only and cannot express
  anchors or stakes.

- **The spine is already in game state — this story only projects it; it does not
  seed, mutate, or own it.** Reads: `quest_log` (`dict[str, QuestEntry]`:
  title/objective/status/anchor_id) at `game/session.py:790`; `quest_anchors`
  (`list[str]`) at `:861`; `active_stakes` (`str`) at `:867`. Seeding/mutation belongs
  to 77-1 (`game/quest_seed.py:seed_quest_spine`) and 77-2
  (`agents/tools/record_quest.py`, `set_stakes.py`) — out of scope here.

- **No Silent Fallbacks.** An empty/unpopulated spine must project a clean,
  well-formed *empty* payload — never null soup, never a swallowed exception. Preserve
  the existing wire-parity omission contract for genuinely-empty fields
  (`tests/protocol/test_wire_parity.py:75-78`). If a quest references an anchor that no
  longer exists, surface it explicitly rather than silently dropping it.

- **Clean wire shape for the UI to mirror.** 77-5 will hand-author a `QuestsPayload`
  TS interface mirroring this projection (the convention used by
  `RelationshipEntryPayload` / `magic.ts` in `sidequest-ui/src/types/payloads.ts`).
  Keep the shape stable, documented, and snake_case on the wire as the other payloads
  are. Document the server source so the UI type can point back to it.

- **OTEL.** The seed (77-1) and tools (77-2) already emit `quest.*` / `stakes.set`
  spans. Per the project OTEL principle, decide whether a projection-*emit* span is
  warranted (so the GM panel can confirm the projection actually fired, not just that
  the spine mutated) — and if you conclude the existing spans are sufficient, **say so
  explicitly** in the assessment. Do not silently skip observability.

- **Python / FastAPI / pydantic v2 / pytest.** Follow the server's existing protocol
  model conventions (pydantic v2, the `protocol/` typed payloads) and the watcher/OTEL
  span-test conventions. Mind the known full-parallel OTEL span-count test deadlock —
  run any span-count-sensitive tests serially (`-n0`) if needed.

## Scope Boundaries

**In scope:**
- A typed outbound QUESTS projection carrying `quest_log` (title + objective + status +
  anchor_id per quest), `quest_anchors` (anchor id + owning quest + beat/location
  resolution where present), and `active_stakes` (string) **together**, analogous to
  the RELATIONSHIPS snapshot payload.
- Reactive emit: the projection (re-)broadcasts when the spine changes via
  seed-at-creation, `record_quest`, or `set_stakes` (mirror how `relationships_emit`
  fires and change-gates).
- Well-formed empty/seeded/populated states.
- Wiring into the live production emit path (NARRATION_END / shared-world frame), so
  the projection is reachable from real turns — not just a serializer that exists in
  isolation.
- Tests: wire-shape (parity-style), per-mutation-path reactive emit, empty/seeded
  states, and **at least one behavioral wiring test** driving a real turn through the
  handler and asserting the projection is emitted to the socket.

**Out of scope:**
- All seeding/mutation logic (77-1, 77-2) and the `quest_anchors`→`WorldStatePatch` /
  orbital wiring (77-3) and one-mechanism cleanup (77-4) — all DONE; this consumes
  their output.
- The UI panel, the `QuestsPayload` TS type, and any rendering — that is 77-5
  (parked, `repos: ui`), which resumes after this merges.
- Defining new seed/tool OTEL spans — those exist. Only a projection-emit span (if
  warranted) is in scope here.
- Any change to the legacy `StateDelta.quests` semantics beyond not regressing its
  existing consumers and the empty-omission contract (AC5).

## AC Context

> ACs are authored on the story (`pf sprint story show 77-8` / `epic-77.yaml`). They
> are the test rubric. Summarized here for test design:

- **AC1 — Rich quests projection on the wire.** The client receives `quest_log`
  (title + objective + status + anchor_id per quest), `quest_anchors` (anchor id +
  owning quest + beat/location resolution), and `active_stakes` (string) together in a
  typed payload analogous to `RelationshipsPayload`. *Test:* serialize a populated
  spine and assert all three fields appear with correct shape on the wire (parity-style,
  like `test_wire_parity.py`).

- **AC2 — Reactive emit on change.** The projection re-broadcasts when
  seed-at-creation, `record_quest`, or `set_stakes` mutate the spine. *Test:* mutate via
  each path → projection carries the new value; unchanged spine → change-gated no-op.

- **AC3 — Empty/seeded states are well-formed.** Unpopulated spine → clean empty-but-
  valid payload (no null soup, no throw); single creation-seeded quest+anchor+stakes →
  exactly that one entry. *Test:* empty snapshot → empty-but-valid payload; seeded
  snapshot → one entry.

- **AC4 — Wiring (reachable from production).** The projection is emitted from the live
  NARRATION_END / shared-world-frame path. *Test (wiring):* drive a turn through the
  handler and assert the quests projection is emitted to the socket — not just a
  serializer unit test.

- **AC5 — No regression.** Does not break legacy `quests` dict consumers or the
  wire-parity omission contract for genuinely-empty fields. *Test:* existing
  `test_wire_parity` assertions still hold for the empty case.

## Interaction Patterns

- **Where it fires.** Peer to the other shared-world frame emissions (location,
  tactical, magic, relationships) in the websocket session handler's emit path on
  NARRATION_END. Change-gated like `relationships_emit` so an unchanged spine does not
  re-broadcast.
- **Shape mirrors RELATIONSHIPS.** A dedicated message type (e.g. `QUESTS`) with a
  payload object: the quest log as a list of typed entries, the anchors as typed
  entries associated to their owning quest, and the active stakes string — clean enough
  for the UI to mirror 1:1 into a TS interface.
- **Read-only projection.** No game logic, no writes; pure serialization of existing
  state.
