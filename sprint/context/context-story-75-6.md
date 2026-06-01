---
parent: "75"
workflow: tdd
---
# Story 75-6 Context — Card sync/reproject hook wired to the 75-1 accretion trigger (ADR-118)

## Business Context

A living world accretes and *mutates* cast and geography (SOUL: *Living
World*, *Diamonds and Coal*). 75-4 built the `EntityCard` model + projectors +
typed `EntityStore`; 75-5 built `retrieve_turn_context` (floor + semantic fill)
that reads that store every turn. But the store is **inert**: nothing populates
it and nothing refreshes it when an NPC's disposition shifts, a location is
discovered, or a faction's stance turns. **75-6 closes the mutation loop** — it
projects the turn's live entities into the store and re-projects the ones that
changed, so the index the narrator retrieves from is the *current* cast, not a
stale or empty one.

This rides the **75-1 accretion trigger**: every turn, `accrete_for_turn`
(`server/dispatch/lore_accretion.py`) sweeps discovered `KnownFact`s into the
lore store right before the embed worker is dispatched. 75-6 adds the sibling
sweep for *entities* at the same seam, so freshly (re)projected cards land in
the pending-embedding queue and are searchable next turn.

**Whom it serves:** Sebastien and Jade (mechanics-first) feel a narrator that
loses track of a responsive, evolving cast. An empty or stale entity index
degrades retrieval for the whole table — the narrator improvises relationships
instead of grounding them. The `accretion.entity_sync` span named here is a
Keith/dev GM-panel lie-detector (it proves the index is being kept fresh) —
**not** a player-facing surface, and not a reason to invoke any playgroup name
on backend observability.

## Technical Guardrails

The canonical, code-level spec lives in the **session file**
(`.session/75-6-session.md`, higher spec authority than this document). The
design of record is **ADR-118 §D2 (dirty-flag reproject)**. These are the
constraints test design must enforce — grounded in the live code the scout read
(2026-06-01):

- **Repo / language:** `sidequest-server` (Python). Base branch: `develop`.
  Apply the `python.md` lang-review checklist.
- **Hook point is the 75-1 seam, not a new one (ADR-118 §D2; SOUL *Don't
  Reinvent*):** the entity sync MUST be invoked from the per-turn flow at the
  same place lore accretion fires — `_execute_narration_turn`
  (`websocket_session_handler.py:1255` calls `self._accrete_lore_for_turn(sd)`,
  then `:1260` `self._dispatch_embed_worker(sd)`). The new
  `_sync_entity_cards_for_turn(sd)` (delegating to a
  `server/dispatch/entity_sync.py`) belongs **between** those two — after
  accretion, before the embed worker — so reprojected cards with
  `embedding_pending=True` are in the queue when the worker dispatches.
- **The store is currently NEVER seeded (scout finding — shapes the wiring
  test):** `project_npc_card` / `project_faction_card` / `project_location_card`
  have **zero production callers**; `_SessionData.entity_store` is a
  `default_factory=EntityStore` that starts empty, so 75-5's
  `retrieve_turn_context` queries an empty store every turn today. 75-6 is the
  story that first populates it. A wiring test MUST prove the store goes
  **empty → populated** after one turn's sync through the production path — not
  merely that a projector returns a card.
- **Reproject is an UPSERT, not an add (scout finding — central contract):**
  `EntityStore.add()` raises `DuplicateEntityId` on an existing id
  (`entity_store.py:45`). Reprojecting a mutated NPC yields the *same* stable id
  (`npc:<slug>`), so a naive `add()` would crash the turn. 75-6 needs a
  replace/upsert path that: (a) overwrites the stored card with the fresh
  projection, and (b) resets `embedding_pending=True` so the worker re-embeds
  the changed content. A test MUST assert that re-syncing a mutated entity does
  NOT raise `DuplicateEntityId` and DOES replace the content + re-arm the
  pending flag.
- **The embed worker must drain `entity_store` too (scout finding — wiring
  gap):** `lore_embed.dispatch_worker` / `run_worker` only call
  `sd.lore_store.pending_embedding_ids` and `embed_pending_fragments(sd.lore_store)`
  (`server/dispatch/lore_embed.py:85,150`). Reprojected `EntityCard`s sit
  `embedding_pending=True` forever — invisible to `query_by_similarity` (which
  skips `embedding is None`) — unless the worker is extended to drain
  `sd.entity_store`. A test MUST prove a synced card's embedding is populated by
  the worker path (read-back), i.e. the entity store is actually drained.
- **Deterministic reproject = no-op when unchanged (ADR-118 §D2 / churn risk):**
  the projectors are deterministic (75-4). 75-6 must exploit that: an entity
  whose state did not change between turns must NOT be needlessly re-embedded
  (no `embedding_pending` re-arm, no embedding churn). A test MUST assert that
  syncing an *unchanged* entity leaves its existing embedding intact
  (`embedding_pending` stays `False`, embedding unchanged). This is the
  dirty-flag's whole point.
- **Dirty detection keys on projected content, not a wall-clock or blanket
  re-sync:** "changed" means the freshly projected `content` differs from the
  stored card's `content` (projection is the source of equality, since the card
  embeds `content`). Disposition *attitude-band* changes count (the NPC
  projector embeds the band, not the raw int) — but a raw-int wiggle inside the
  same band does NOT (it projects identical content → no churn). Tests must
  cover both: a band-crossing change re-arms; a within-band change does not.
- **No Silent Fallbacks (SOUL):** an entity that cannot be projected (projector
  raises — e.g. a blank-named NPC, a location with no description) must surface
  loud: counted as a failed projection, logged, and reflected in the span
  (`outcome="partial"` / a failure count) — never silently skipped to a stub
  card. A test MUST assert the loud path (the sync does not swallow the raise
  into a silent success, and does not emit a placeholder card).
- **Accretion failure isolation is inherited, NOT discarded (mirror 75-1):**
  `accrete_for_turn` wraps its sweep so a failure is logged + emitted as an
  `op="failed"` watcher event + swallowed — feeding the index must never cost
  the player their narration. 75-6's entity sync MUST adopt the identical
  discipline: a catastrophic sync failure is isolated, emits a failure
  watcher/span, and returns — it does not raise into the turn. A test MUST
  assert a thrown internal error does not propagate out of the turn-level entry.
- **OTEL span is mandatory and uses the 75-4 attribute contract (project
  doctrine; ADR-118 §D5):** emit `accretion.entity_sync` carrying at least the
  reproject count (`SPAN_CARD_REPROJECT_COUNT = "card_reproject_count"`,
  `entity_card.py`), per-type counts, and an `outcome`
  (`"success"` / `"partial"` / `"skipped"`). The GM panel is the lie-detector;
  a sync that fires no span is indistinguishable from improvisation. A test MUST
  assert the span (or its watcher-event equivalent) fires with the reproject
  count.
- **Zero-byte-leak (no empty work):** a turn with no entities to sync and
  nothing dirty emits `outcome="skipped"` and writes no cards — it does not push
  an empty batch into the store or the embed queue. A test MUST assert the
  no-dirty turn is a clean skip.
- **Meaningful assertions only (TEA self-check):** assert *card content,
  pending-flag state, store membership, and span attribute values* — never
  `assert card is not None` where the field value is the contract. No
  `let _ =`-equivalent, no `assert True`, no `is None` on an always-None value.

## Scope Boundaries

**In scope:**
- A turn-level entity-sync entry — `_sync_entity_cards_for_turn(sd)` on the
  handler, delegating to a new `server/dispatch/entity_sync.py` (sibling of
  `lore_accretion.py`), wired into `_execute_narration_turn` between accretion
  and the embed-worker dispatch.
- A pure sync function (game tier, e.g. `game/entity_sync.py` or extend
  `entity_card`/`entity_store`) that: collects the turn's projectable entities
  (NPCs from `npc_pool`, factions from world state, locations from the
  normalized source 75-5 already reads), projects each, and **upserts** into
  `entity_store` — re-arming `embedding_pending` only when projected content
  changed. Returns a result dataclass (mirror `AccretionResult`):
  reprojected/unchanged/failed counts + per-type counts.
- An **upsert/replace** method on `EntityStore` (e.g. `upsert(card)`) that
  overwrites by id and re-arms `embedding_pending` on content change, leaving an
  unchanged card untouched.
- Extending the embed-worker drain (`lore_embed`) to also drain
  `sd.entity_store` (pending ids → embed → `update_embedding`), OR a sibling
  entity-embed dispatch — the cards MUST get embedded by the live worker path.
- The `accretion.entity_sync` OTEL span + watcher event (reproject/unchanged/
  failed counts, per-type counts, `outcome`), using the 75-4 attribute-name
  constants.
- Unit tests for the sync function + upsert + dirty/no-dirty/failed paths, an
  embed-worker read-back test for entity cards, and the production-reachable
  wiring test (empty → populated → refreshed across two turns).

**Out of scope (do not let tests demand these):**
- **The `EntityCard` model / projectors / store query surface** — that is
  **75-4** (merged). 75-6 consumes the projectors and adds upsert; it does not
  redefine cards or re-implement cosine/query.
- **Per-turn retrieval orchestration** (`retrieve_turn_context`, floor+fill,
  Valley-zone injection) — that is **75-5** (merged). 75-6 keeps the store the
  orchestrator reads *fresh*; it does not run or alter the retrieval pass.
- **Lore accretion itself** (`accrete_for_turn`, KnownFact → LoreFragment) —
  that is **75-1** (merged). 75-6 hooks the *same seam* for entities; it does
  not touch the lore sweep.
- **OTEL GM-panel surfacing / dashboard wiring + the unified retrieval span
  emission `retrieval.universal`** — that is **75-7**. 75-6 emits its own
  `accretion.entity_sync` span; it does not build the panel view or the
  retrieval-span emitter.
- **End-to-end action→sync→floor+fill→Valley integration** — that is **75-8**.
  75-6's wiring test proves sync populates/refreshes the store; the full
  retrieval-to-narration e2e is 75-8.
- **System-of-record migration to Postgres rows (ADR-118 §D1):** the index is
  in-memory like `LoreStore`; entities stay snapshot-carried. No persistence
  migration.
- **A formal per-entity dirty-flag field on the source structs:** dirty
  detection is by projected-content comparison against the stored card (the
  determinism 75-4 guarantees) — 75-6 does not add a mutable `dirty` bit to
  `NpcPoolMember`/`Faction` unless content-comparison proves insufficient (and
  if it does, that is a logged deviation).

## AC Context

The story YAML carries no template ACs; the authoritative spec is the session
file's **Implementation Contract** + **Test Design Guardrails** (lines
100–164). Derived test obligations:

1. **Sync populates an empty store through the production seam.**
   *Tests:* drive one turn's sync on a snapshot with NPCs/factions/locations →
   `entity_store` is non-empty, cards present per type, ids namespaced
   (`npc:`/`faction:`/`loc:`).
2. **Reproject upserts a mutated entity (no DuplicateEntityId).**
   *Tests:* sync, mutate an NPC's disposition across an attitude band, sync
   again → no raise; stored card `content` reflects the new band;
   `embedding_pending` re-armed to `True`.
3. **Unchanged entity is a deterministic no-op (no churn).**
   *Tests:* sync, give the card an embedding (simulate worker), sync again with
   unchanged state → `embedding_pending` stays `False`, embedding unchanged,
   reproject count excludes it.
4. **Within-band disposition wiggle does NOT re-arm.**
   *Tests:* mutate the raw disposition int without crossing the attitude band →
   projected content identical → unchanged path.
5. **Embed worker drains entity_store (read-back).**
   *Tests:* after sync, the live worker path embeds the pending entity cards;
   `update_embedding` clears the flag; `query_by_similarity` can now rank them.
6. **`accretion.entity_sync` span fires with reproject count + outcome.**
   *Tests:* assert span/watcher event emitted with `card_reproject_count` (or
   the per-type counts) and `outcome` ∈ {success, partial, skipped}.
7. **Loud failure on an unprojectable entity (No Silent Fallbacks).**
   *Tests:* an entity whose projector raises → counted as failed,
   `outcome="partial"`, NO stub card added, error logged.
8. **No-dirty turn is a clean skip (zero-byte-leak).**
   *Tests:* a turn with no entities / nothing changed → `outcome="skipped"`, no
   cards written, no pending-queue growth.
9. **Turn-level entry isolates failure (inherited from 75-1).**
   *Tests:* force an internal error in the sync → `_sync_entity_cards_for_turn`
   does NOT raise out of the turn; failure watcher/span emitted.
10. **Wiring test (mandatory; project doctrine):** across **two** real turns —
    turn 1 populates the store from empty; mutate an entity; turn 2 refreshes
    it — assert the orchestrator-visible store reflects the mutation. Reachable
    from `_execute_narration_turn`, not an isolated unit.

**Negative / paranoia cases beyond the AC minimum:**
- Upsert of an entity whose content is unchanged but whose embedding is `None`
  (never embedded) → stays pending, not double-queued.
- A faction and an NPC that slug to colliding-looking ids stay distinct (the
  `npc:`/`faction:` namespace prevents collision) — sync of both coexists.
- Empty snapshot (no NPCs, no factions, no locations) → `outcome="skipped"`,
  store untouched.
- A blank-named NPC in the pool → projector raises → failed count, no crash, no
  stub.
- Re-running sync twice in the SAME turn is idempotent (no duplicate work, no
  re-arm of already-fresh cards).

## Assumptions

- **75-1, 75-2, 75-4, 75-5 are merged** (waterfall, ADR-118 §Composition). 75-6
  may assume the accretion seam, the floor, the card model/projectors, and the
  retrieval pass all exist live.
- **The embed worker is extensible to a second store** the same way it drains
  lore: `pending_embedding_ids` → embed → `update_embedding` is a generic
  contract `EntityStore` already implements (`entity_store.py:88,134`). If
  draining two stores in one worker proves structurally awkward, a sibling
  entity-embed dispatch is acceptable — but the cards MUST be embedded by the
  live worker, not a test-only path. If this proves false, log a deviation.
- **Dirty detection by projected-content equality is sufficient** for v1. The
  projectors are deterministic and embed exactly the fields that matter
  (attitude band, not raw int), so content-equality is the correct churn gate.
  If some entity carries retrieval-relevant state the projector does *not* embed
  (so a meaningful change is invisible to content-comparison), that is a
  projector gap — log it as a finding for 75-4 follow-up, do not paper over it
  with a blanket re-embed.
- **The normalized location source 75-5 reads is the same one 75-6 syncs from.**
  75-6 does not re-solve the diffuse location problem; it projects from whatever
  normalized view `retrieve_turn_context` already consumes. If locations are
  deferred in 75-5's live form, 75-6 ships NPCs + factions and logs the location
  deferral as a deviation (ADR-118 permits the NPC+faction-first v1).
- **`entity_ref` is a back-pointer only** (ADR-118 §D1) — reproject reads source
  state and writes the card; it never mutates the source struct. Tests must not
  assert the sync changes `npc_pool`/`Faction` state.

---
_Authored by The Architect (TEA) during RED-phase context recovery, 2026-06-01.
The `sm-setup` run created the session file but skipped this standalone
story-context document — the identical `sm-setup` gap recovered for 75-4 in
commit `e091713`. The context gate (`pf validate context-story 75-6`) and
downstream test strategy require it. Sources: ADR-118 (§D2 dirty-flag reproject,
§D5 span names, §Composition waterfall), the session file's Implementation
Contract, sibling 75-4 context (model/store contract), and a live read of
`server/dispatch/lore_accretion.py`, `server/dispatch/lore_embed.py`,
`game/entity_card.py`, `game/entity_store.py`, `game/retrieval_orchestration.py`,
and the `_execute_narration_turn` seam in `websocket_session_handler.py`
(2026-06-01). Two scout findings reshape scope beyond the session's prose: the
store is never seeded today (sync is also the seeder), and the embed worker does
not yet drain `entity_store` (75-6 must extend it). The session file remains the
higher-authority spec; this document is the test-strategy lens TEA's gate
requires._
