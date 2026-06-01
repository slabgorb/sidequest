---
parent: "75"
workflow: tdd
---
# Story 75-4 Context — EntityCard model + per-type projectors + typed store generalization (ADR-118)

## Business Context

A living world accretes cast and geography (SOUL: *Living World*,
*Diamonds and Coal*). Today the narrator is fed the **full** snapshot every
turn: the entire `npc_pool` blob plus all location/POI state, dumped into
`TurnContext` regardless of relevance. The lore RAG already fixes this for
*lore* — it embeds discovered facts and retrieves by similarity each turn
(`lore_embedding.py:276` `retrieve_lore_context` → `LoreStore.query_by_similarity`
→ `orchestrator.py:2096`, `AttentionZone.Valley`). **But NPCs, locations, and
factions were never RAG-indexed in either the Rust origin or Python** — they
ride the snapshot in full, so a long session's roster and map crowd out the
prompt budget while relevance is never consulted.

ADR-118 (Universal Retrieval Layer) closes that gap with a **floor + fill**
retrieval that indexes NPCs/locations/factions into the *same* vector machinery
lore already uses. **75-4 is the foundation slice of that layer**: it defines
the uniform `EntityCard` projection, the per-type `to_card()` projectors, and
the typed-store generalization — the storage substrate every later story
(75-5 orchestration, 75-6 sync, 75-7 OTEL, 75-8 e2e) builds on. Get the model
and store wrong and the entire universal-retrieval waterfall stands on sand.

**Whom it serves:** Sebastien and Jade (mechanics-first) feel a narrator that
loses track of a responsive, relevant cast; an unbounded snapshot blob degrades
narration for the whole table. The OTEL spans named here (defined now, *emitted*
in 75-7) are a Keith/dev GM-panel lie-detector — **not** a player-facing
surface, and not a reason to invoke any playgroup name on backend observability.

## Technical Guardrails

The canonical, code-level technical approach lives in the **session file**
(`.session/75-4-session.md`, higher spec authority than this document). The
design of record is **ADR-118 §D1–D3**. These are the constraints test design
must enforce:

- **Repo / language:** `sidequest-server` (Python). Base branch: `develop`.
  Apply the `python.md` lang-review checklist.
- **Reuse-first, do NOT rebuild (ADR-118 D3; SOUL *Don't Reinvent*):** the
  embedding worker, `cosine_similarity`, `query_by_similarity`,
  `requeue_dimension_mismatched`, `update_embedding`, `pending_embedding_ids`,
  and the daemon MiniLM-L6-v2 path are **already built, tested, and live** in
  `lore_store.py` / `lore_embedding.py`. 75-4 generalizes that machinery typed
  by `entity_type` — **no new embedding model, no schema migration, no forked
  worker.** A test that re-implements cosine math instead of exercising the
  shared path is a red flag.
- **`EntityCard` is a structural sibling of `LoreFragment`** (`lore_store.py:70`).
  It MUST carry the identical worker contract fields so the existing embedding
  worker drains it unchanged: `embedding` / `embedding_pending` (default
  `True`) / `embedding_retry_count` (default `0`), plus `id`, `entity_type`,
  `entity_ref`, `content`, `token_estimate`, `metadata`. Pydantic `BaseModel`,
  mirroring `LoreFragment`'s construction pattern (`LoreFragment.new(...)`).
- **Stable, namespaced card IDs (ADR-118 D3):** `"npc:<id>"`, `"loc:<id>"`,
  `"faction:<id>"`. The `entity_type` prefix is part of the contract — tests
  must pin the format, and the typed store must be able to filter by it
  (cf. `LoreStore.query_by_category`).
- **Deterministic projection (ADR-118 D3 / dual-rep risk):** the same
  entity state MUST project to the same `content` every time (stable field
  order — e.g. sorted goal/member lists) so embeddings don't churn on
  re-projection. A test must assert `to_card()` is deterministic across repeated
  calls on unchanged state. (The dirty-flag *reproject hook* itself is 75-6 — do
  not build it here, but the determinism it relies on is 75-4's responsibility.)
- **Blank-content rejection** mirrors `LoreFragment._content_must_not_be_blank`:
  an `EntityCard` (or projector) with empty/whitespace `content` must fail loud,
  not embed an empty string. Test `EntityCard.new("")`-equivalent → raises.
- **`token_estimate` is computed, not trusted from the caller** — reuse the
  `_estimate_tokens` approach so floor/fill budgeting (75-5) has an honest cost.
- **No Silent Fallbacks (SOUL):** a projector that cannot render an entity
  (e.g. a faction not present in game state, a location whose source is
  unrecognized) must raise an explicit error — never silently emit a placeholder
  card or skip the entity. A test must assert the loud failure.
- **Diffuse location sources (ADR-118 D3 / Negative-risk):** the location
  projector must adapt per source — room graph, `world_materialization`, and PG
  `location_promotions` — not read one uniform pool. Tests must cover at least
  two distinct location sources, or, if v1 defers locations (ADR-118 names this
  as a permitted fallback: ship NPCs + factions first), that deferral MUST be
  logged as a deviation and the scope reflected in the session spec.
- **Wiring test is mandatory (project doctrine; SM risk flag):** at least one
  integration test must prove the typed store is reachable and usable from a
  real game-context construction path — synthesize a scenario with NPCs /
  locations / factions, project cards, add them, and query by type/similarity —
  not merely unit-correct projectors in isolation.
- **Meaningful assertions only (TEA self-check):** assert *card field values and
  store query results*, never `assert card is not None` where the field value is
  the real contract. No `let _ =`-equivalent, no `assert True`, no `is None` on
  an always-None value.

## Scope Boundaries

**In scope:**
- The `EntityCard` model (`sidequest/game/entity_card.py`, new) — sibling of
  `LoreFragment`, identical worker-contract fields, blank-content validation,
  computed `token_estimate`, namespaced stable IDs.
- The per-type projectors: `NpcCardProjector`, `LocationCardProjector`,
  `FactionCardProjector` (or equivalent `to_card()` surface) rendering
  deterministic embeddable `content` from each entity's system-of-record home.
- Typed-store generalization (`sidequest/game/entity_store.py`, new — OR a typed
  extension of `LoreStore`): `add`, `query_by_type`, `query_by_similarity`
  (reusing the shared cosine/worker machinery), token accessors, save/load
  round-trip with embeddings intact.
- Unit tests for every projector + store, an embedding-worker read-back test,
  and the production-reachable wiring test.
- **OTEL span *attributes/definitions* prepared** (`card_reproject_count`,
  `stale_card_count`, the `retrieval.universal` attribute names per ADR-118 D5)
  — **shape defined, NOT emitted.**

**Out of scope (do not let tests demand these):**
- **Per-turn retrieval orchestration** — `retrieve_turn_context`, floor+fill,
  the budget seam, Valley-zone injection. That is **75-5**. 75-4 makes cards
  *queryable*; it does not run the per-turn pass.
- **Dirty-flag sync / reproject hook** wired to 75-1 accretion — that is
  **75-6**. 75-4 guarantees projection *determinism* (so reproject is safe) but
  builds no mutation trigger.
- **OTEL *emission* + GM-panel surface** — that is **75-7**. Define attribute
  names here; emit nothing.
- **End-to-end action→floor+fill→Valley wiring** — that is **75-8**.
- **The NPC working-set floor** (recency tiers) — that is **75-2** (merged); its
  selection *is* the floor consumed by 75-5, not re-derived here.
- **Accretion / lore re-feed** — **75-1** (merged).
- **System-of-record migration to Postgres rows (ADR-118 D1):** the index is
  in-memory like `LoreStore`; entities stay snapshot-carried. No persistence
  migration in this story.
- **Events/history and inventory card types (ADR-118 D2):** events ride the lore
  RAG; inventory is out of v1 scope. No card type for either.

## AC Context

The seven ACs (verbatim source: session file `## Acceptance Criteria`) and what
each demands of test design:

1. **`EntityCard` model defined** — `id`, `entity_type`, `entity_ref`,
   `content`, `token_estimate`, `embedding`/`embedding_pending`/
   `embedding_retry_count`, `metadata`.
   *Tests:* field presence + defaults (`embedding_pending=True`,
   `embedding_retry_count=0`); namespaced-ID format (`npc:` / `loc:` /
   `faction:`); blank `content` rejected; `token_estimate` computed from content.

2. **Per-type projectors wired** — NPC (name/role/pronouns/disposition/goals/
   key facts from `NpcPoolMember`/`Npc`), Location (name/description/mechanics/
   linked NPCs, adapting per diffuse source), Faction (goals/attitude/members).
   *Tests:* one projector test per type asserting the projected `content`
   contains the contracted fields; location projector exercised against ≥2
   sources (or deferral logged).

3. **Typed store generalization** — holds `EntityCard`s, reuses embedding
   worker + cosine + dimension-mismatch requeue; filter/query by `entity_type`;
   query by similarity.
   *Tests:* `add` then `query_by_type` returns only that type; `query_by_similarity`
   ranks by cosine over cards with embeddings; dimension-mismatch requeue behaves
   as it does for lore.

4. **No retrieval orchestration wiring** — cards exist and are queryable in
   isolation; no per-turn loop.
   *Tests:* a guard/scope assertion that 75-4 introduces no `retrieve_turn_context`
   caller (or simply: the per-turn path is untouched — verified by absence, and
   by the deferral note). Primarily a scope boundary for the author, not a
   behavioral test.

5. **Tests cover all entity types** — projector + construction + token estimate
   + store add/query + embedding worker read-back.
   *Tests:* embedding round-trip — a card with `embedding_pending=True` is drained
   by the same worker path lore uses and `update_embedding` clears the flag.

6. **Wiring test included** — store reachable/usable from real game context:
   synthesize a scenario (NPCs + locations + factions) → project → add → query
   by type → assert retrieval works in a non-isolated path.
   *Tests:* the mandatory integration test (project doctrine).

7. **OTEL spans prepared (no wiring yet)** — `card_reproject_count`,
   `stale_card_count`, `retrieval.universal` attribute names defined per D5;
   emitted by 75-5/75-7.
   *Tests:* assert the attribute-name constants/definitions exist and are the
   D5-contracted strings — **do not** assert emission (that would over-reach into
   75-7). If definitions live as constants, a test pins their names.

**Negative / paranoia cases test design should add (beyond the AC minimum):**
- Empty/whitespace `content` → projector or `EntityCard` constructor raises.
- Unknown location source → loud failure, no placeholder card (No Silent
  Fallbacks).
- Faction absent from game state → projector raises, not a silent empty card.
- Projection determinism → `to_card()` twice on unchanged state yields identical
  `content` (and identical embedding-relevant ordering of list fields).
- Duplicate card ID into the store → mirror `DuplicateLoreId` behavior (raise),
  not silent overwrite.
- `query_by_similarity` with a dimension-mismatched embedding → requeues rather
  than silently scoring 0.0 (the `requeue_dimension_mismatched` contract).
- Save/load round-trip preserves `embedding` and `embedding_pending` state.

## Assumptions

- **75-1 and 75-2 are merged** (waterfall, ADR-118 §Composition). 75-4 may
  assume live accretion exists and that 75-2's selection is the floor consumed
  *downstream* (by 75-5) — 75-4 itself neither calls nor re-derives the floor.
- **The embedding worker is polymorphic-by-extension, not by rewrite:** the
  existing `pending_embedding_ids` / `update_embedding` drain path can be made to
  also consume `EntityCard`s with `embedding_pending=True` without a new worker
  process or model. If this proves false in the code, log a deviation — it
  changes the reuse story.
- **One typed store vs. sibling index is an implementation detail bounded by
  75-4** (ADR-118 D3): the retrieval *contract* is identical either way. Tests
  assert behavior (query-by-type, similarity, token accounting), not the
  physical store-vs-sibling choice.
- **Location sources are diffuse but enumerable** (room graph,
  `world_materialization`, PG `location_promotions`). If the POI sources are not
  yet consolidated enough to project cleanly, ADR-118 explicitly permits a v1
  that ships **NPCs + factions first** and defers locations — that deferral is a
  logged deviation, not silent scope-cutting.
- **`entity_ref` is a back-pointer only** (ADR-118 D1) — the card owns no truth;
  the system-of-record struct remains authoritative. Tests must not assert the
  card mutates source state.

---
_Authored by The Architect (TEA) during RED-phase context recovery, 2026-06-01.
The `sm-setup` run created the session file but skipped this standalone
story-context document, which the context gate (`pf validate context-story 75-4`)
and downstream test strategy require. Sources: ADR-118 (§D1–D3 model/store
contract, §D5 span names, §Composition waterfall), epic-75 context (scout
audit), sibling 75-2 context (floor framing), and the live `lore_store.py` /
`lore_embedding.py` machinery this story generalizes. The session file remains
the higher-authority spec; this document is the test-strategy lens TEA's gate
requires._
