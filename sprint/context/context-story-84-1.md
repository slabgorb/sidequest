# Story 84-1 Context

## Title
WI-1 Unified pertinence scorer + present-scene invariant + drama-gated embed (supersedes ADR-118 §D4)

## Metadata
- **Story ID:** 84-1
- **Type:** story
- **Points:** 5
- **Priority:** p2
- **Workflow:** tdd
- **Repo:** sidequest-server
- **Epic:** 84 — ADR-118 Amendment — Unified Pertinence Scorer & Tiered Forgetting

## Problem
The live ADR-118 §D4 retrieval (`sidequest/game/retrieval_orchestration.py::retrieve_turn_context`)
splits per-turn entity selection into two mechanisms: a binary **floor** (scene-present
NPCs, via `build_npc_working_set`) and a similarity-ranked **fill** (cosine top-k over the
`EntityStore`). The structured pertinence model Keith always intended — **mention ≫ location
> recency, with embedding similarity only as a fallback** — was only ever realized for NPCs;
every other entity type can only be reached through the weak similarity tail. The §D4 fill
ALSO embeds on every turn, paying the expensive daemon `embed(action)` round-trip even when
the player named a present entity ("I attack Borin").

The 2026-06-04 ADR-118 amendment §A1 replaces the floor/fill split with **one weighted,
scored selection**, a **present-scene hard invariant**, and a **drama-gate** that skips the
embed when structured signals already suffice. WI-1 is the foundation story — every other
Epic-84 work item (WI-2…WI-6) rides this spine.

## Technical Approach
- **New module `sidequest/game/pertinence.py`** owns the pure scorer (no I/O, no daemon):
  - `PertinenceWeights` (frozen): `w_mention`, `w_location`, `w_recency`, `w_sim` — the single
    GLOBAL tuning vector. `DEFAULT_PERTINENCE_WEIGHTS` must encode `w_mention > w_location >
    w_recency > 0` AND `w_mention > w_location + w_recency + w_sim` (mention is dominant, not
    merely first).
  - `PertinenceSignals` (frozen): per-card computed signal values `mention`, `here`, `recency`
    (all `0..1`), `sim: float | None` (None encodes "embed skipped this turn"), and
    `present_scene: bool`.
  - `PertinenceScore` (frozen): per-signal contributions (`mention_contribution`,
    `here_contribution`, `recency_contribution`, `sim_contribution`), the combined `score`,
    `card_id`, `present_scene`, and `embed_used` (False when the drama-gate skipped cosine).
    This struct is the A5/WI-6 OTEL `retrieval.card.reason` payload.
  - `SIGNAL_APPLICABILITY: dict[str, frozenset[str]]` — per `EntityType`, which of the four
    signals apply. `SIGNAL_MENTION`/`SIGNAL_HERE`/`SIGNAL_RECENCY`/`SIGNAL_SIM` string consts.
    A non-applicable signal contributes **0** to the score (no nonsense terms).
  - `score_card(card, signals, weights=DEFAULT_PERTINENCE_WEIGHTS) -> PertinenceScore` —
    weighted sum over the APPLICABLE signals only; a `sim=None` (skipped embed) contributes 0
    and sets `embed_used=False`.
  - `structured_signals_sufficient(signals) -> bool` — the drama-gate predicate: True when
    mention + here come back strong enough to skip the cosine pass.
  - `select_within_budget(scores, cards_by_id, *, budget_tokens) -> list[EntityCard]` —
    admits all `present_scene` cards FIRST and unconditionally (exempt from the budget), then
    fills the remainder by descending score.
- **Rewrite `retrieve_turn_context`** (`sidequest/game/retrieval_orchestration.py`) to use the
  unified scorer instead of the floor/fill split:
  - Compute structured signals (mention via `player_referenced_npcs_from_action` /
    alias-match seam, here via scene-presence, recency via `last_seen_turn` decay) BEFORE
    embedding.
  - **Drama-gate:** only call `client.embed(action)` when `structured_signals_sufficient`
    returns False for the turn's candidate pool. On a named/present action the embed is
    SKIPPED entirely.
  - Rank with `score_card` + `select_within_budget`; the present-scene entities are never
    evicted.
  - **Extend `RetrievedEntities`** with `embed_skipped: bool` and `card_scores:
    list[PertinenceScore]` while KEEPING the existing consumer fields
    (`floor`, `retrieved_npcs/locations/factions`, `outcome`, the count fields) so
    `session_helpers.py` (renderer) and `server/dispatch/universal_retrieval.py` (watcher)
    keep working unchanged.
  - Emit `retrieval.embed_skipped` on the existing `retrieval.universal` span (WI-6 adds the
    full per-card decomposition; WI-1 lands the one boolean the wiring test asserts).

## Scope
- **In scope:** the §A1 unified scorer, the present-scene hard invariant, the drama-gated
  embed, per-type signal applicability, the `retrieve_turn_context` rewrite that supersedes the
  §D4 floor/fill split, and the `RetrievedEntities` extension. Land the `retrieval.embed_skipped`
  span attribute (the wiring observable).
- **Out of scope (other Epic-84 stories):** alias resolution / accretion-fed aliases (WI-5,
  84-2) — WI-1 may use the existing `player_referenced_npcs_from_action` name-match as the
  mention signal placeholder; relationship card projector (WI-4, 84-3); the full A5 per-card
  OTEL decomposition + GM-panel surface (WI-6, 84-4); lifecycle-aware dormant/active scope
  (WI-2, 84-5); tiered projection / lazy demote / vector-shedding (WI-3, 84-6).
- **Do NOT** delete §D1–D3/§D5 (the index, the embedding-worker contract, the dirty-flag
  reproject, the span shape). §A1 only changes how a projected card is *scored and selected*.

## Acceptance Criteria

> Each AC is covered by failing tests written in the RED phase (see Test Coverage below).

- **AC-1 — Unified weighted score replaces the floor/fill split.** `score_card` produces
  `score = Σ wᵢ·signalᵢ` over the signals applicable to the card's entity type, with the
  per-signal contributions reported. `DEFAULT_PERTINENCE_WEIGHTS` encodes `mention > location
  > recency > 0` and `mention > location + recency + sim` (mention is dominant).
  *Tests:* `test_score_is_weighted_sum_of_applicable_signals`,
  `test_default_weights_enforce_mention_dominates_location_dominates_recency`,
  `test_named_entity_outranks_merely_similar_entity`.

- **AC-2 — Per-type signal applicability.** `SIGNAL_APPLICABILITY` declares, for every
  `EntityType`, which of the four signals apply; an NPC declares `here` applicable; a
  non-applicable signal contributes 0 to the score (one global weight vector, no per-type
  weight terms). *Tests:* `test_applicability_declared_for_every_entity_type`,
  `test_npc_declares_here_as_applicable`, `test_inapplicable_signal_does_not_contribute_to_score`.

- **AC-3 — Present-scene HARD invariant.** An entity the player is physically engaging
  (`present_scene=True`) is admitted regardless of its weighted score and CANNOT be budgeted/
  evicted out — even under a zero remaining budget. The invariant is a constraint on selection,
  not an emergent weight property. *Tests:*
  `test_present_scene_entity_survives_budget_even_with_low_score`,
  `test_present_scene_not_dropped_even_when_budget_is_zero`,
  `test_present_scene_flag_propagates_to_score`,
  `test_present_npc_never_dropped_under_tight_budget` (orchestration level).

- **AC-4 — Drama-gated embedding.** `structured_signals_sufficient` returns True when mention
  + here are strong (skip the cosine embed) and False when signals are thin (run the cosine
  fallback). A skipped embed sets `embed_used=False` and contributes 0 to `sim` (no phantom
  similarity — No Silent Fallbacks). End-to-end: a named/present action does NOT call the
  daemon `embed`; a thin action DOES. *Tests:*
  `test_strong_structured_signals_are_sufficient_skip_embed`,
  `test_thin_structured_signals_are_insufficient_require_embed`,
  `test_skipped_embed_marks_embed_used_false_and_sim_zero`,
  `test_present_embed_marks_embed_used_true`,
  `test_named_present_action_skips_the_daemon_embed`,
  `test_thin_action_still_embeds_as_fallback`.

- **AC-5 — Supersedes §D4 without breaking consumers.** `retrieve_turn_context` keeps the
  public `RetrievedEntities` shape (`floor`, `retrieved_npcs/locations/factions`, `outcome`)
  the renderer + watcher depend on, and ADDS `embed_skipped: bool` plus `card_scores:
  list[PertinenceScore]`. *Tests:* `test_result_still_exposes_consumer_fields` (regression
  guard — passes against old + new), `test_selected_cards_carry_pertinence_scores`,
  `test_present_npc_never_dropped_under_tight_budget`.

- **AC-6 — WIRING.** Driving a real `PlayerActionMessage` through `WebSocketSessionHandler`
  reaches `retrieve_turn_context` on the live turn path (`retrieval.universal` span fires);
  naming a scene-present NPC SKIPS the daemon embed for that turn; the span carries
  `retrieval.embed_skipped=True`. Behavior + span only — no source-text grep. *Test:*
  `test_named_present_action_skips_embed_on_live_turn`.

- **AC-7 — Quality gate.** All ACs have failing test coverage before GREEN; tree clean, no
  debug code, correct branch (`feat/84-1-unified-pertinence-scorer`) at the GREEN gate;
  `just server-check` green; `retrieval.universal` span still fires every turn.

## Test Coverage (RED — failing tests in place)
- `sidequest-server/tests/game/test_pertinence_scorer.py` — pure scorer unit/contract spec
  (weights ordering, weighted sum, applicability matrix, present-scene flag/invariant,
  drama-gate predicate, embed_used semantics). 14 tests.
- `sidequest-server/tests/game/test_unified_retrieval_supersedes_d4.py` — orchestration-level
  supersession (drama-gate fires/skips end-to-end, per-card score decomposition exposed,
  `RetrievedEntities` back-compat, present-scene invariant under tight budget). 5 tests.
- `sidequest-server/tests/game/test_pertinence_wiring.py` — production wiring through
  `WebSocketSessionHandler` (span fired + named-action embed skipped + `retrieval.embed_skipped`
  span attribute). 1 test.

## Notes for Dev
- The mention signal in WI-1 may reuse the existing word-bounded
  `player_referenced_npcs_from_action` (`sidequest/agents/npc_context.py`). Alias/epithet
  resolution is WI-5 (84-2) — do not build it here, but leave the mention computation behind a
  seam WI-5 can extend.
- `RetrievedEntities` is a `@dataclass(frozen=True)`. Adding `embed_skipped` + `card_scores`
  must keep every existing field (consumers: `server/session_helpers.py:1155-1258`,
  `server/dispatch/universal_retrieval.py:75-96`). Defaulting the new fields is fine but they
  must be POPULATED, not silently defaulted (No Silent Fallbacks).
- The live call path the wiring test exercises:
  `websocket_session_handler.py:3170 _retrieve_entities_for_turn`
  → `server/dispatch/universal_retrieval.py:60 retrieve_for_turn`
  → `game/retrieval_orchestration.py:159 retrieve_turn_context` (the scorer plugs in here).

---
_Acceptance criteria authored by TEA (Amos Burton) during the RED phase from the
ADR-118 amendment §A1 + the 84-1 session brief. Supersedes the generated placeholder._
