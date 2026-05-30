---
parent: context-epic-72.md
workflow: trivial
---

# Story 72-8: Stamp last_seen on encounter presence

**Epic:** 72 (NPC Identity Hardening) · **Points:** 2 · **Type:** bug · **Repo:** sidequest-server

## Business Context

`Npc.last_seen_turn` / `Npc.last_seen_location` are the engine's recency record
for "when/where did we last actually see this person." Today they are stamped
**only** when the narrator names the NPC in prose — the `npcs_hit` branch of
`_apply_npc_mentions` (`sidequest/server/narration_apply.py:1239–1242`). An NPC
who is *physically present in an encounter* (seated as an opponent, dial/HP being
mutated round over round) but who happens not to get named in that turn's
`npcs_present` prose mentions goes **un-stamped**. The engine treats a combatant
the party has been fighting for six rounds as "not recently seen."

This is wrong on its own terms — presence is a stronger continuity signal than a
prose name-drop — and it is load-bearing for the rest of epic 72:

- **72-6 (cap `npc_pool` growth, LRU/last-seen prune)** evicts stale members by
  recency. If presence doesn't refresh `last_seen_*`, an actively-fought NPC looks
  stale to the LRU and becomes an eviction candidate while still on the board.
- **`_npc_fallback_at_location`** (`encounter_lifecycle.py:420–493`) *reads*
  `last_seen_location` to decide who to seat into an encounter when the narrator
  dropped the adversary. A presence-stamp keeps that fallback population coherent
  turn over turn instead of decaying.
- The GM panel (Keith's lie-detector) should be able to confirm that an NPC the
  party is demonstrably interacting with has fresh recency state, not stale state
  that silently misrepresents the table.

## Technical Guardrails

**The two paths (verified):**

1. **Prose-mention path (working, do not regress).**
   `_apply_npc_mentions` → `npcs_hit` branch stamps
   `npc_hit.last_seen_location = actor_loc` and
   `npc_hit.last_seen_turn = turn_num`
   (`narration_apply.py:1239–1242`), gated on a name match in `npcs_present`.

2. **Encounter-presence path (the gap this story closes).**
   `_seed_combat_hp_depletion_to_npcs` (`encounter_lifecycle.py:103–184`) iterates
   the encounter `actors`, matches or creates the backing `Npc` in
   `snapshot.npcs`, mutates its HP pool, and emits one `npc_edge_published_span`
   per opponent write — but **never** stamps `last_seen_turn` / `last_seen_location`.
   The companion dial-path `_publish_combat_stats` (~line 266) has the same shape.

**Where to stamp:** the encounter-presence seam already has what it needs.
`_seed_combat_hp_depletion_to_npcs` receives `turn: int` (line 108) and holds the
matched/created `npc` object before emitting `npc_edge_published_span`
(lines 175–183) — stamp there, beside the edge-published emit, so presence and the
HP write are the same atomic moment. Location resolves via
`snapshot.party_location(perspective=acting_character_name)` — the same accessor
the prose path and `_npc_fallback_at_location` (line 472) already use. Do **not**
invent a second location source; reuse that accessor (No Silent Fallbacks).

**Fields (verified):** `Npc.last_seen_location: str | None = None`
(`session.py:157`) and `Npc.last_seen_turn: int = 0` (`session.py:160`). Turn
counter starts at 1; `0` means "never seen this session." No model change needed.

**OTEL:** per the epic span plan, the presence stamp should be observable. The
`npc_edge_published_span` already fires at this exact seam — surface the stamped
`last_seen_turn` / `last_seen_location` as attributes there (or on a sibling span)
so the GM panel can confirm presence-stamping fired, rather than adding a brand-new
span family. Cosmetic-only changes don't need OTEL, but this is a subsystem
decision (recency state mutated), so it must be visible.

**Server test rule (CLAUDE.md "No Source-Text Wiring Tests"):** assert *behavior*,
not source shape. Construct a snapshot with an NPC seated as an encounter opponent,
drive the real `_seed_combat_hp_depletion_to_npcs` (or the dispatch that calls it),
and assert the `Npc`'s `last_seen_turn` / `last_seen_location` were updated — and/or
assert the OTEL span carries the stamped values. Never grep production source as a
wiring assertion.

## Scope Boundaries

**In scope:**
- Stamp `last_seen_turn` / `last_seen_location` on the encounter-**presence** seam
  (`_seed_combat_hp_depletion_to_npcs`, and the parallel `_publish_combat_stats`
  dial path if it seats opponents the same way), using the existing `turn` and the
  `party_location` accessor.
- Surface the stamped values on the existing `npc_edge_published_span`.

**Out of scope:**
- Do **not** touch the prose-mention stamp logic except to confirm it still fires —
  it is correct.
- Do **not** implement the LRU/prune eviction itself (that is 72-6; this story only
  guarantees the field 72-6 will read is accurate).
- No `Npc` model changes (fields already exist).
- No change to `_npc_fallback_at_location` read semantics, to seating/membership
  invariants (ADR-116, owned by 72-1/72-2/other stories), or to disposition.

## AC Context

Derived (no explicit ACs on a trivial bug):

1. **Presence stamps even without prose mention.** An NPC seated as an encounter
   opponent and processed through the encounter-presence seam has
   `last_seen_turn` set to the current turn and `last_seen_location` set to the
   acting character's resolved location — even when that NPC's name is absent from
   this turn's `npcs_present` prose mentions.

2. **Prose-mention stamping still works (no regression).** An NPC named in
   `npcs_present` still gets `last_seen_turn` / `last_seen_location` stamped via the
   existing `npcs_hit` branch.

3. **Recency field is consumable by recency logic.** After a presence stamp, the
   NPC's `last_seen_turn` reflects the encounter turn (the value 72-6's LRU
   eviction reads), and `_npc_fallback_at_location`'s `last_seen_location` read sees
   the refreshed value.

**Edge cases to cover:**
- **Present AND mentioned (no inconsistent double-stamp).** When an NPC is both
  seated in the encounter and named in prose the same turn, both paths write the
  same `turn_num` / same resolved location — final state is one consistent stamp,
  not two conflicting values.
- **NPC leaves the encounter.** Once an NPC is no longer a seated opponent, the
  presence path stops stamping; their `last_seen_*` correctly stays frozen at the
  last turn they were present (it does not keep advancing), so 72-6's staleness
  measure works.
- **No resolved location.** If `party_location(...)` returns `None` (seated PCs
  disagree / no location), do not write a bogus location — mirror the prose path,
  which only writes `last_seen_location` when `actor_loc` is truthy, while still
  stamping `last_seen_turn`.

## Assumptions

- `_seed_combat_hp_depletion_to_npcs` (`encounter_lifecycle.py:103`) is the
  authoritative encounter-presence seam for opponent NPCs; `_publish_combat_stats`
  (~line 266) is the legacy dial-threshold sibling and gets the same stamp if it
  seats opponents identically. If a third presence seam exists (e.g. non-opponent /
  neutral participants joined via `participant_joined_span`), the implementer
  should stamp there too — presence means presence, not just opponent-side.
- The acting character name needed for `party_location(perspective=...)` is
  reachable at this seam (the same value the calling dispatch already threads for
  HP/location resolution). If it is not in scope here, fall back to the
  party-frame `party_location()` consensus accessor — never to a hardcoded or
  silently-defaulted location.
- 72-6 (LRU/prune) is a sibling backlog story and is **not yet implemented** in
  `npc_pool.py`; this story does not consume it. The dependency runs the other way:
  72-6 will read the `last_seen_turn` this story makes accurate, so correct
  stamping here is a precondition for 72-6 not mis-evicting active NPCs.
- Turn counter is 1-based (`last_seen_turn = 0` ⇒ never seen). The `turn` passed to
  the encounter seam is the same interaction-turn number the prose path uses, so
  the two paths produce comparable values.
