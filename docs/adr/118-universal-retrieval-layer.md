---
id: 118
title: "Universal Retrieval Layer — Index + Per-Turn Floor-and-Fill Retrieval for NPCs, Locations, and Factions"
status: accepted
date: 2026-05-31
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [14, 48, 59, 87, 104, 115]
tags: [agent-system, npc-character, observability]
implementation-status: deferred
implementation-pointer: null
---

# ADR-118: Universal Retrieval Layer

> **Design-only ADR (no code in story 75-3).** This record defines the
> universal retrieval layer and names the follow-on implementation stories.
> It is the third thread of Epic 75 (RAG Retrieval Layer). Threads 75-1
> (accretion restoration) and 75-2 (budgeted NPC working-set selection) are
> separate stories; this ADR states what they deliver versus what the
> universal layer adds on top, and how the three compose.

## Context

A scout audit (2026-05-30, verified against the Rust origin
`github.com/slabgorb/sidequest-api` and the current Python tree) established
the ground truth the prior status badges obscured:

- **The lore RAG is real and fires every turn.** Entry at
  `websocket_session_handler.py:2456` → `_retrieve_lore_for_turn()` →
  `lore_embedding.py:276` `retrieve_lore_context()` (real MiniLM-L6-v2 384-dim
  embeddings via the daemon) → injection at `orchestrator.py:2096`
  (`AttentionZone.Valley`). `LoreStore.query_by_similarity()` does live cosine
  ranking. The seam is OTEL-instrumented and fail-quiet.
- **But it is lore-only.** NPCs, locations/POIs, and factions were **never**
  RAG-indexed in either Rust or Python. They are *snapshot-carried*: the full
  `npc_pool` blob and full location/POI state are dumped into `TurnContext`
  every turn (`orchestrator.py` NPC carry; locations diffuse across the room
  graph, `world_materialization`, `history_chapter.points_of_interest`, and PG
  `location_promotions`). This does not scale with a living world: a long
  session accretes cast and geography until the snapshot dominates the prompt
  budget, yet relevance is never consulted — the narrator sees *everything*
  every turn, present or not.

The opportunity: a **universal retrieval layer** where lore + NPCs + locations
+ factions are indexed into a shared vector store and retrieved per turn by
relevance, under a token budget, instead of snapshot-dumped in full — while
never dropping the entity the player is physically interacting with.

This ADR makes five load-bearing decisions, each resolved with Keith during
the 2026-05-31 design session.

## Decision

### D1 — Persistence: index overlay on existing state (not system-of-record migration)

NPCs, locations, and factions **remain snapshot-carried structures**; their
system-of-record stays exactly where it lives today (`npc_pool`, room graph,
faction state, save file / PG per ADR-115). The universal layer is a
**retrieval *index* layered on top** — it owns no truth, only projections.

Rejected: promoting entities to queryable Postgres rows as the system of
record. That is a large migration with a wide blast radius across the
persistence layer for a benefit (durable SQL+vector query) this design does
not yet need. The index is in-memory like `LoreStore`. A future PG promotion
is namable as follow-on work and is *not* foreclosed: the retrieval contract
(D4) is written to be persistence-agnostic so the backing store can change
without changing callers.

**Consequence / named risk:** dual representation (live struct + index card)
requires a sync discipline. Addressed in D3.

### D2 — Index scope: NPCs, locations/POIs, factions; events ride the lore RAG

The universal layer indexes **NPCs, locations/POIs, and factions**. **Events
and history are *not* a separate entity type** — discovered facts (including
"what happened") flow through the lore RAG via the 75-1 accretion path, which
already embeds them. Adding an events card type would double-index the same
discovered facts. **Inventory is out of scope for v1** (low narrative leverage
relative to its sync cost; namable later).

### D3 — The `EntityCard` abstraction + reuse the `LoreStore` machinery

Define a uniform, embeddable projection — a structural sibling of
`LoreFragment` (`lore_store.py:70`):

```
EntityCard:
  id            # stable: "npc:borin", "loc:black_hart", "faction:tide_syndicate"
  entity_type   # "npc" | "location" | "faction"
  entity_ref    # back-pointer to the system-of-record struct (no data ownership)
  content       # the embeddable text projection (drives the embedding)
  token_estimate
  embedding / embedding_pending / embedding_retry_count  # identical worker contract
  metadata      # provenance, last_seen turn, region, disposition tier, ...
```

**Reuse-first (do not rebuild):** the embedding worker, `cosine_similarity`,
`query_by_similarity`, the dimension-mismatch requeue
(`requeue_dimension_mismatched`), and the daemon MiniLM-L6-v2 path are all
already built, tested, and live for lore. The universal index is the **same
machinery, typed by `entity_type`** — no new embedding model, no schema
migration. The recommendation is **one typed store** (lore being a type within
it, or a sibling index sharing the identical worker) so the "universal" claim
is real at the storage layer; category-style filtering (cf.
`LoreStore.query_by_category`) keeps lore-only queries clean. The physical
one-store-vs-sibling-index split is an implementation detail bounded by 75-4;
the retrieval *contract* (D4) is identical either way.

**Card projection (the authoring/sync surface):** each entity type provides a
`to_card()` projector that renders its embeddable `content`:

- **NPC** → name, role, pronouns, disposition tier, goals, key facts
  (projected from `NpcPoolMember` / promoted `Npc`).
- **Location/POI** → name, description, mechanical properties, linked NPCs
  (projected from the entity's existing home — room graph, materialization, or
  PG promotion; the projector adapts per source, since locations are diffuse).
- **Faction** → goals, attitude toward the party, notable members/resources.

**Sync discipline (resolves the D1 risk):** cards re-project on
system-of-record mutation via a **dirty-flag → embedding-worker reproject**
hook. **75-1's accretion is the natural trigger** — when world state changes,
affected cards are marked dirty and the existing embedding worker re-embeds
them on its next pass (same path that already drains `embedding_pending`
lore). Staleness is **observable, never silent** (`stale_card_count`,
`card_reproject_count` — see D5), honoring *No Silent Fallbacks*.

### D4 — Per-turn retrieval: floor + fill, one budgeted pass

Pure semantic top-k can miss the entity *physically present this turn* if the
action text does not embed near that entity's card — the narrator would lose
someone standing in the room. Resolution: a **guaranteed floor plus semantic
fill**.

```
FLOOR  = 75-2 working-set selection (scene-present entities:
         last_seen ≤ N turns, current location's NPCs/POI)
         → ALWAYS included, full detail, counted against the budget FIRST.
FILL   = embed(action text) once → semantic top-k over the NON-floor cards
         → fill the remaining budget (budget − floor_cost) until exhausted,
           applying a similarity floor (cf. DEFAULT_RETRIEVAL_MIN_SIMILARITY).
INJECT = AttentionZone.Valley (the same zone lore uses today), as typed
         sections (retrieved_npcs / retrieved_locations / retrieved_factions),
         with zero-byte-leak discipline (None → no section registered).
```

**75-2's selection *is* the floor; 75-3's retrieval is the fill.** Nothing
present is ever dropped (Guitar Solo: the soloist's scene stays whole;
Diamonds-and-Coal: detail tracks relevance; ADR-014 Living World: entities move
*in and out of context* by relevance, never by deletion).

This generalizes `retrieve_lore_context` into a `retrieve_turn_context`
orchestration that runs lore + entity retrieval under **one total per-turn
token budget** (floor counted first, fill consumes the remainder). The contract
is persistence-agnostic (D1): it takes a query string, a budget, and a floor
set, and returns budgeted, type-tagged sections — independent of whether the
backing store is in-memory or (future) Postgres.

### D5 — OTEL observability (doctrine-mandated; Keith's lie detector)

Per ADR-031 / ADR-090 / ADR-103 and the project OTEL principle, the retrieval
seam must let the GM panel verify retrieval *engaged* rather than the narrator
improvising. A new `retrieval.universal` span emits, mirroring the existing
`lore.*` attribute discipline:

- `retrieval.budget_total`, `retrieval.outcome`
- `retrieval.floor_count`, `retrieval.floor_token_cost`
- `retrieval.fill_candidate_count`, `retrieval.fill_selected_count`,
  `retrieval.fill_token_cost`
- per-type counts: `retrieval.npc_count`, `retrieval.location_count`,
  `retrieval.faction_count`
- `retrieval.rejected_below_similarity`, `retrieval.dimension_mismatch_count`
- failure paths: query embed failed, daemon unavailable, budget exhausted
  before fill, no relevant entities — each a distinct `outcome` value, never a
  silent skip.

Card-sync emits `card_reproject_count` and `stale_card_count` so a stale index
is visible in the GM panel rather than silently serving outdated projections.

## Composition with 75-1 and 75-2 — waterfall

The three Epic 75 threads sequence as a **waterfall**, each landing on stable
ground beneath it:

1. **75-1 (accretion restoration)** — restores the per-turn fact-feed
   (Rust `lore_sync.rs:26-120` `accumulate_and_persist_lore`) so the index has
   live discovered lore to ingest, **and** becomes the trigger that marks
   `EntityCard`s dirty for reprojection (D3).
2. **75-2 (budgeted working-set selection)** — ports the Rust
   `npc_context.rs:11-86` selection (scene-present full, others abbreviated,
   **no eviction**) and becomes **the deterministic floor** (D4).
3. **75-3 (this design) → implementation** — layers the universal index and
   semantic fill on top of a working floor.

Rationale for waterfall over parallel: 75-3's floor *is* 75-2's selection, and
75-1's accretion *feeds* the index — the data dependencies are real, so
sequencing minimizes integration risk and keeps test boundaries clean.

## Implementation stories (this ADR spawns)

Story 75-3 delivers **design only**. The following stories implement it
(assume 75-1 and 75-2 are merged first per the waterfall):

- **75-4 — `EntityCard` + per-type projectors + typed store generalization.**
  Define `EntityCard`, the `to_card()` projectors for NPC/location/faction,
  and generalize the `LoreStore` machinery to a typed universal index.
- **75-5 — `retrieve_turn_context` floor+fill orchestration + budget seam.**
  Generalize `retrieve_lore_context`; implement floor (75-2 selection) + fill
  (semantic top-k) under one token budget; Valley-zone typed injection with
  zero-byte-leak.
- **75-6 — Card sync/reproject hook.** Wire the dirty-flag → embedding-worker
  reproject path to 75-1's accretion trigger.
- **75-7 — OTEL `retrieval.universal` instrumentation + GM-panel surface.**
  Emit the D5 spans/attributes and surface them in the dashboard.
- **75-8 — Integration wiring test.** End-to-end: player action → floor+fill
  selection → Valley injection → narrator prompt, with the wiring test the
  project mandates (component reachable from a production code path).

## Reconciliation with existing ADRs

- **ADR-048 (Lore RAG Store with Cross-Process Embedding):** extended, not
  replaced. The universal layer reuses ADR-048's embedding pipeline and
  `LoreStore` query machinery wholesale.
- **ADR-059 (Monster Manual — Game-State Injection):** the full-NPC-blob
  snapshot injection is **superseded** by budgeted floor+fill for the
  retrieved-NPC channel. (ADR-059's pre-generation role is unaffected; only the
  *every-turn full-blob carry* is replaced.)
- **ADR-087 (Post-Port Subsystem Restoration Plan):** 75-1/75-2/75-3 are the
  restoration+expansion tasks tracked there; this ADR is their design of
  record.
- **ADR-014 (Diamonds and Coal / Living World):** honored — no entity is ever
  deleted; entities move in and out of prompt context by relevance, and the
  floor guarantees the present scene stays whole.
- **ADR-104 (Perception Filtering at the Tool Layer):** the retrieval layer
  selects *what is relevant*, not *what a given player may perceive*. Perception
  filtering remains the tool/broadcast layer's job; retrieved cards are subject
  to it downstream, unchanged.
- **ADR-115 (PostgreSQL Persistence Substrate):** unaffected — system-of-record
  stays where it lives; the index is in-memory (D1). A future PG promotion of
  the index is namable and not foreclosed by this design.

## Consequences

**Positive:**

- Prompt cost stops growing without bound as the cast and geography accrete;
  relevance, not recency-of-existence, governs what the narrator sees.
- Maximal reuse of a tested, live seam (embedding worker, cosine query,
  dimension-mismatch guard) — minimal new surface, no new model, no migration.
- The present scene is never dropped (floor), satisfying the SOUL doctrines.
- Every retrieval decision is observable in the GM panel (D5).

**Negative / risks:**

- **Dual representation** (live struct + index card) requires the sync
  discipline of D3; a missed reproject means a stale card. Mitigated by the
  accretion-triggered dirty-flag and the `stale_card_count` span.
- **Diffuse location sources** mean the location projector must adapt per
  source (room graph / materialization / PG promotion) rather than reading one
  uniform pool — more projector surface than NPCs. If this proves costly, v1
  may ship NPCs + factions first and add locations once the POI sources are
  consolidated (flagged for 75-4).
- **Budget tuning** (total per-turn token budget, similarity floor, floor size
  N) needs playtest calibration; the D5 spans provide the data.

## Alternatives considered

- **System-of-record migration to Postgres rows (D1):** rejected for blast
  radius; deferred as future work behind the persistence-agnostic contract.
- **Pure semantic replace (no floor) (D4):** rejected — risks dropping a
  physically-present entity from context.
- **Floor only, retrieval deferred (D4):** considered as a de-risking path;
  rejected because it does not deliver the "universal" recall promise in this
  epic, though the floor (75-2) does land first under the waterfall.
- **Separate embedding models per entity type (D3):** rejected — one unified
  MiniLM-L6-v2 already serves lore; per-type models add operational surface for
  no demonstrated relevance gain.
- **75-3 absorbs the floor / fold 75-2 in:** rejected — muddies the epic's
  clean three-thread framing and inflates a single story.
