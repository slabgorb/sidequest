---
id: 118
title: "Universal Retrieval Layer — Index + Per-Turn Floor-and-Fill Retrieval for NPCs, Locations, and Factions"
status: accepted
date: 2026-05-31
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [14, 48, 59, 87, 102, 104, 109, 115, 128, 136]
tags: [agent-system, npc-character, observability]
implementation-status: live
implementation-pointer: "Core (D1–D5) live: sidequest-server/sidequest/game/retrieval_orchestration.py + entity_card.py + dispatch/universal_retrieval.py — retrieve_turn_context called every narrator turn. The 2026-06-04 amendment (unified pertinence scorer / lifecycle-aware scope / tiered forgetting) is design-only — implementation pending; see the Amendment section."
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
  `websocket_session_handler.py` → `_retrieve_lore_for_turn()` →
  `lore_embedding.py` `retrieve_lore_context()` (real MiniLM-L6-v2 384-dim
  embeddings via the daemon) → injection at `orchestrator.py`
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
`LoreFragment` (`lore_store.py`):

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
   (Rust `lore_sync.rs` `accumulate_and_persist_lore`) so the index has
   live discovered lore to ingest, **and** becomes the trigger that marks
   `EntityCard`s dirty for reprojection (D3).
2. **75-2 (budgeted working-set selection)** — ports the Rust
   `npc_context.rs` selection (scene-present full, others abbreviated,
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

## Amendment — Unified Pertinence Scorer, Lifecycle-Aware Scope, and Tiered Forgetting (2026-06-04)

> **Design-only amendment (no code in this change).** It records decisions made
> with Keith in the 2026-06-04 design session and names the follow-on
> implementation work. The core layer (D1–D5) remains **live and unchanged in
> behavior** until that work lands; this amendment redefines the *target* design.

**Trigger.** The original ADR framed retrieval as a per-session continuity aid.
The load-bearing reframing in this session: SideQuest campaigns are meant to run
for **years**, so the accreted world (lore, cast, geography, quests, tropes,
relationships) grows without bound while the per-turn prompt budget does not.
Retrieval is therefore not a feature but *the* mechanism that lets the narrator
behave like a human DM — who holds the current scene in their head and **consults
notes on demand** when a player names something. Two facts forced the amendment:
(1) the structured pertinence model Keith has always intended — **mention ≫
location > recency, with embedding similarity as the *fallback*** — was only ever
realized for NPCs (the §D4 floor is `npc_context`-shaped; 75-10 wired the NPC
mention signal), while every other type can only be reached by the weak
similarity tail; and (2) ADR-048 (Consequences, final bullet) records that **"no
eviction policy exists yet"** — nothing in the design survives years of
accretion. This amendment **supersedes §D2 and §D4 in part** and **extends
ADR-048** by supplying the missing forgetting policy.

### A1 — Unify the floor and fill into one pertinence score (supersedes §D4)

§D4's two-mechanism split (binary floor + similarity-ranked fill) is replaced by
**one scored selection**:

```
score(card) = w_mention·mention(card, action, aliases)   # dominant
            + w_location·here(card, snapshot)            # is it here / adjacent
            + w_recency·decay(card.last_seen, now)       # recently touched
            + w_sim·cosine(embed(action), card)          # topical fallback
→ rank all candidates, take until the per-turn token budget is exhausted.
```

The §D4 *floor guarantee* survives, not as a separate mechanism but as a **hard
invariant on top of the ranking**: a card for an entity the player is
**physically engaging this turn cannot be budgeted out**, full stop. This keeps
the SOUL *Guitar Solo* / ADR-014 *Living World* promise as an explicit assertion
rather than an emergent property of weights.

**Drama-gated embedding (SOUL *Cost Scales with Drama*).** The `w_sim·cosine`
term is the only expensive signal (it requires `embed(action)` via the daemon).
It is **computed only when the structured signals come back thin** — i.e. when
the action named nothing and the party is nowhere specific. "I attack Borin"
resolves entirely on mention + location; the embed is **skipped**. This is
strictly cheaper than the current always-embed fill.

**Weights (resolved leans, this session):** signals are **per-type in
*applicability*, global in *weight*.** Each entity type declares *which* of the
four signals apply to it (e.g. `here` is load-bearing for an NPC, inapplicable to
a free-floating lore fact); the *weight* of each signal it uses is a single
global tuning vector. One knob, no nonsense terms.

### A2 — Lifecycle-aware index scope: index the dormant, floor the active (supersedes §D2)

§D2's flat `npc | location | faction` scope is widened and made **lifecycle-aware**:

```
indexed (recall-by-pertinence):  npc · location · faction · relationship
                                 · DORMANT quest · DORMANT trope
floor-only (imposed, never recalled):  ACTIVE quest · ACTIVE trope
lore:  unchanged — rides the 75-1 accretion path, not a card type (per §D2)
```

The distinction (Merovingian's correction in the design session): an **active**
trope or quest is *pressure on the table* — it applies whether or not anyone
named it, so it belongs in the floor unconditionally. A **dormant/completed** one
is a *note* — looked up only when referenced ("what was that quest about the
smuggler?"). Each type declares an **active/dormant predicate**
(`QuestStatus`, the ADR-128 governor state); only the dormant side is projected
into the index. Nothing is deleted on completion (ADR-014) — a finished quest
becomes a dormant, lookup-able note.

**Relationships are always index-side** (resolved lean): a relationship is never
its own floor pressure. It surfaces because the related NPC is named or present —
the NPC's floor-presence (or a mention) pulls the relationship card in.

### A3 — Acceptable forgetting: tiered projection, lazy demotion, vector-shedding (extends ADR-048)

This supplies the eviction policy ADR-048 lacks — as **demotion, not deletion**,
so *Living World* holds.

- **Tiers.** `to_card(tier ∈ {FULL, SUMMARY, INDEX})` renders progressively less
  of the same system-of-record struct. Tier is `metadata.tier`.
- **Lazy demotion.** A note demotes on **read-miss** (it was a candidate but lost
  the budget cut, repeatedly), never on a global timer — this avoids a
  re-embedding stampede across thousands of cold cards. Demotion re-projects via
  the existing §D3 dirty-flag → embedding-worker path.
- **Vector-shedding.** An **INDEX-tier card drops its embedding** and survives on
  the *non-vector* structured signals only — `mention` (alias-match) and
  `here` (graph lookup). This directly bounds ADR-048's "384-dim vectors per
  fragment … non-trivial memory cost at long durations": the cold tail sheds its
  vectors.
- **Rehydration.** A **mention always rehydrates a card to FULL** (re-projects,
  re-embeds) — when a player says the name, the DM reads the whole page.
- **Accepted behavior (ruled):** a cold, un-named, un-located note *does* fall
  out of semantic reach until something rehydrates it. That is the DM correctly
  forgetting the minor NPC nobody asked about — not a defect.
- **Named rescue hatch (deferred, out of scope here):** a `consult_notes(entity)`
  retrieval **tool** (ADR-102 tool-use) lets the narrator pull a cold card
  mid-turn when the pre-fetch missed an oblique reference. Tracked as follow-on,
  not built in this amendment.

### A4 — Supports

- **Relationship card ≡ summary-tier card.** The `disposition_log` (ADR-136) is a
  time series and cannot be embedded whole; the relationship card is *born* at
  SUMMARY tier — current attitude band + the two or three load-bearing beats. The
  decay machine (A3) and the relationship projector are therefore the **same
  shape**.
- **Alias-aware, accretion-fed mention.** `mention` resolves through each card's
  **aliases/epithets**, not raw player tokens (ADR-048's own example: "the Ember
  Throne" ≡ "the seat of the fire king"). World-authored entities carry aliases
  in YAML; **promoted/yes-and entities accrete epithets** via the 75-1 accretion
  path — mention-matching gets smarter the longer the campaign runs, with no new
  pipeline. Without this, the dominant signal degrades to keyword matching.

### A5 — OTEL: per-card score decomposition (extends §D5)

A weighted scorer that cannot be audited is improvisation with a number attached.
Each *selected* card emits its **score breakdown** so the GM panel shows *why* a
note surfaced and supplies weight-calibration data:

- `retrieval.card.reason` per selected card: the four signal contributions
  (`mention`, `here`, `recency`, `sim`) and the final score.
- `retrieval.embed_skipped` (bool) — whether the drama-gate skipped the cosine
  pass this turn (A1).
- `retrieval.tier_demotions`, `retrieval.tier_rehydrations`,
  `retrieval.vectors_shed` — the A3 forgetting lifecycle, never silent.

These extend the §D5 attribute set; the existing `retrieval.universal` span is
unchanged in shape, only enriched.

### Reconciliation with existing ADRs (delta)

- **ADR-048 (Lore RAG):** extended — A3 supplies the eviction policy 048's
  Consequences records as missing. Lore fragments become tier-able and
  vector-sheddable like any other card.
- **ADR-128 (Trope Governor):** the governor's active/dormant state *is* the A2
  predicate for tropes. Active tropes ride the floor (unchanged); dormant tropes
  become indexed notes.
- **ADR-136 (Relationship Surface):** the player-facing RELATIONSHIPS projection
  and the A4 relationship *card* both project from the same disposition data;
  the card is the *retrieval* projection (index-side, A2), orthogonal to the
  reactive player surface.
- **ADR-109 (Persistent Location Descriptions):** the diffuse-location projector
  (§D3) is unchanged; A1/A2 only change how a location *card*, once projected, is
  scored and tiered.
- **ADR-102 (Tool-Use Protocol):** the deferred `consult_notes()` rescue hatch
  (A3) is a future tool, explicitly out of this amendment's scope.
- **ADR-014 (Diamonds & Coal / Living World):** preserved — forgetting is
  demotion + vector-shed, never deletion; the present scene is never dropped (A1
  invariant).

### Implementation work (spawns a follow-on epic; story IDs assigned in sprint planning)

The core (D1–D5) stays live throughout; these land incrementally on top.

- **WI-1 — Unified pertinence scorer + present-scene invariant + drama-gated
  embed.** Replace the §D4 floor/fill split with the A1 scored selection; per-type
  signal applicability, global weights; skip the embed when structured signals are
  thin. Wiring proven by OTEL/behavior, not source-text.
- **WI-2 — Lifecycle-aware scope.** Active/dormant predicate per type; index
  dormant quests/tropes + relationships; route active quests/tropes to the floor.
- **WI-3 — Tiered projection + lazy demotion + vector-shedding.** `to_card(tier)`;
  demote-on-read-miss; INDEX-tier drops embedding; mention rehydrates to FULL.
- **WI-4 — Relationship projector (summary-tier).** Project `disposition_log` →
  attitude + key beats; index-side only.
- **WI-5 — Alias resolution + accretion-fed aliases.** Alias-aware mention match;
  promoted entities accrete epithets via the 75-1 path.
- **WI-6 — OTEL score decomposition.** Emit the A5 attributes; surface in the GM
  panel.

Sequencing lean: WI-1 first (it is the new spine every other item rides);
WI-5 close behind (it hardens WI-1's dominant signal); WI-3/WI-4 share the
tiering machine and pair; WI-2 and WI-6 are independent. Value-first cut for the
playgroup (per the 140-turn `coyote_star` relationship-carried session):
**WI-1 + WI-5 + WI-4** ship the felt win — mention-driven full-history NPC recall —
before the years-scale tiering (WI-3) and the breadth (WI-2).

### Consequences (delta)

**Positive:**

- The structured pertinence model (mention ≫ location > recency) becomes
  *universal* across all indexed types, not NPC-only; similarity drops to its
  intended role as the topical fallback.
- Prompt cost falls twice: relevance already bounded growth (original ADR); the
  drama-gate now also skips the embed on named/located turns.
- The years-scale gap is closed without deletion — the cold tail fades and sheds
  vectors, the warm core stays sharp, and a mention always reads the full page.
- Every selection is explainable in the GM panel (A5) — the lie-detector now
  covers *ranking*, not just engagement.

**Negative / risks:**

- **Tuning surface.** The four global weights + the tier-demotion threshold + the
  drama-gate "thinness" cutoff all need playtest calibration; A5's per-card
  decomposition is the instrument for it.
- **Acceptable-forgetting edge.** A long-dormant entity referenced *obliquely*
  (no name, no place) is unfindable until rehydrated. Ruled acceptable; the
  deferred `consult_notes()` tool is the eventual rescue.
- **Alias correctness is load-bearing.** A weak alias set degrades the dominant
  signal to keyword match; A4's accretion path is essential, not optional.
