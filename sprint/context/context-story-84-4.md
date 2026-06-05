# Story 84-4 Context

## Title
WI-6 OTEL score decomposition — per-card retrieval.card.reason + embed_skipped + tier lifecycle spans (extends ADR-118 §D5)

## Metadata
- **Story ID:** 84-4
- **Type:** story
- **Points:** 2
- **Priority:** p2
- **Workflow:** tdd
- **Repo:** sidequest-server
- **Epic:** 84 — ADR-118 Amendment — Unified Pertinence Scorer & Tiered Forgetting

## Problem
84-1 (WI-1, merged PR #673) delivered the unified pertinence scorer: `retrieve_turn_context`
populates `RetrievedEntities.card_scores: list[PertinenceScore]` (each carrying the four
per-signal contributions `mention`/`here`/`recency`/`sim` + final `score` + `embed_used`)
and sets `retrieval.embed_skipped` on the `retrieval.universal` span. But that decomposition
**does not reach the GM panel** — and a weighted scorer the GM can't audit is, per ADR-118
§A5, "improvisation with a number attached." Two concrete gaps:

1. The `retrieval.universal` span carries only the §D5 *counts* — there is NO per-card
   `retrieval.card.reason` attribute, so the GM panel cannot show WHY each fill card surfaced
   (which signal dominated, the contribution breakdown).
2. The GM-panel reader path is the **WatcherHub event stream**, not raw OTLP spans. The
   watcher event published by `server/dispatch/universal_retrieval.retrieve_for_turn` carries
   the §D5 counts but **omits `embed_skipped` entirely** and omits the per-card breakdown — so
   the drama-gate decision and the score reasons are invisible on the dashboard even though the
   span (Jaeger-only) has `embed_skipped`.

ADR-118 §A5 also names the tier-lifecycle observables (`retrieval.tier_demotions`,
`tier_rehydrations`, `vectors_shed`). The demotion/rehydration/vector-shed LOGIC lands in
WI-3 (84-6); WI-6's job is to emit the SHAPE now (honest zero-state counters + each selected
card's present tier) so WI-3 extends an existing schema instead of inventing one — **no dead
lifecycle stub code**.

## Technical Approach
> OTEL plumbing only. NO scorer/algorithm change — read `card_scores` + `embed_skipped` that
> 84-1 already populates and surface them on both the span and the watcher event.

- **Per-card reason payload (pure helpers, net-new).** A small pure boundary (e.g.
  `sidequest/telemetry/retrieval_reason.py` or a function block beside `pertinence.py`):
  - `dominant_signal(score: PertinenceScore) -> str` — the name (`"mention"`/`"here"`/
    `"recency"`/`"sim"`) of the highest-contributing signal for that card (the "why it
    surfaced" headline). Ties resolve deterministically by the §A1 priority order
    mention > here > recency > sim.
  - `card_reason_payload(score: PertinenceScore) -> dict` — a JSON-serializable dict:
    `{card_id, mention, here, recency, sim, score, dominant, embed_used, tier}` where the
    four signal keys are the *contributions* from `PertinenceScore`. `tier` is the card's
    present projection tier (real now: there is one tier today — emit it honestly, do not
    fabricate demoted tiers).
- **Span side (`retrieve_turn_context` / `_finish`).** Add `retrieval.card.reason` as a
  **JSON-encoded** span attribute (a list of per-card payloads — OTEL attributes can't hold a
  list of dicts natively, so JSON-encode the list into one string attribute, mirroring the
  watcher's `_coerce_attr_value` discipline). Add the zero-state lifecycle counters
  `retrieval.tier_demotions` / `retrieval.tier_rehydrations` / `retrieval.vectors_shed` = 0.
  Extend `UNIVERSAL_RETRIEVAL_SPAN_ATTRS` (in `entity_card.py`) to include `retrieval.embed_skipped`,
  `retrieval.card.reason`, and the three lifecycle counters — the span-contract test reads this set.
- **Watcher side (`server/dispatch/universal_retrieval.retrieve_for_turn`).** Add to the
  published `state_transition` event fields: `embed_skipped` (bool, currently MISSING) and
  `card_reasons` (the list of per-card payloads — `_coerce_attr_value` JSON-stringifies it
  for the synthetic span, and the dashboard reads it from the raw event fields). This is the
  load-bearing change — without it the GM panel never sees the decomposition.

## Scope
- **In scope:** the per-card `retrieval.card.reason` span attribute + `card_reasons` watcher
  field; `embed_skipped` on the watcher event; the three zero-state tier-lifecycle counters;
  the `dominant_signal` / `card_reason_payload` pure helpers; extending the span-attr contract
  set.
- **Out of scope:** any change to the scorer, the drama-gate, the floor/fill selection, the
  budget, or the `PertinenceScore` shape (84-1 is frozen). The tier-lifecycle LOGIC
  (demote-on-read-miss, rehydrate, vector-shed) is WI-3/84-6 — emit only the present tier and
  zero counters. No UI/dashboard-component work (the TS `WatcherEvent` already round-trips
  arbitrary fields; the React panel is a separate story if a bespoke view is wanted).
- **No dead code:** do NOT add demotion/rehydration functions that nothing calls. Emit only
  what is real this turn.

## Acceptance Criteria

> Each AC is covered by failing tests written in the RED phase (see Test Coverage).

- **AC-1 — Per-card reason decomposition exists.** `card_reason_payload(score)` returns a
  JSON-serializable dict carrying `card_id`, the four signal *contributions*
  (`mention`/`here`/`recency`/`sim`), `score`, `dominant`, `embed_used`, and `tier`.
  `dominant_signal(score)` returns the highest-contributing signal name, resolving ties by the
  §A1 priority order. *Tests:* `test_card_reason_payload_has_all_signal_contributions`,
  `test_dominant_signal_picks_largest_contribution`,
  `test_dominant_signal_breaks_ties_by_priority_order`,
  `test_card_reason_payload_is_json_serializable`.

- **AC-2 — Span carries the per-card reason.** The `retrieval.universal` span emits a
  `retrieval.card.reason` attribute (JSON-encoded list, one entry per SELECTED fill card) whose
  decoded entries match the selected cards' decompositions; on a turn with no fill (gate-skip
  or no candidates) the attribute is an empty JSON list, never absent or malformed.
  *Tests:* `test_span_emits_card_reason_for_each_selected_card`,
  `test_span_card_reason_empty_list_on_gate_skip`.

- **AC-3 — `embed_skipped` reaches the GM-panel reader (watcher event).** The
  `state_transition` event published by `retrieve_for_turn` carries `embed_skipped` matching
  the result's value (True on a named/present drama-gate skip, False on a thin embed). *Tests:*
  `test_watcher_event_carries_embed_skipped_true_on_gate_skip`,
  `test_watcher_event_carries_embed_skipped_false_on_fill`.

- **AC-4 — Per-card reasons reach the GM-panel reader (watcher event).** The published event
  carries `card_reasons` — the list of per-card payloads — so the dashboard can render the
  decomposition from the WatcherHub stream (not just Jaeger). *Tests:*
  `test_watcher_event_carries_card_reasons_for_selected_cards`.

- **AC-5 — Tier-lifecycle SHAPE present, zero-state, no dead logic.** The span carries
  `retrieval.tier_demotions` / `retrieval.tier_rehydrations` / `retrieval.vectors_shed`, all
  `0` this turn (the logic is WI-3); each card-reason payload carries the card's present `tier`.
  *Tests:* `test_span_emits_zero_state_tier_lifecycle_counters`,
  `test_card_reason_payload_reports_present_tier`.

- **AC-6 — Span-attribute contract updated.** `UNIVERSAL_RETRIEVAL_SPAN_ATTRS` includes
  `retrieval.embed_skipped`, `retrieval.card.reason`, and the three lifecycle counters, and the
  live span carries every name in the set (the §D5 contract test). *Tests:*
  `test_span_attr_contract_includes_wi6_attributes`,
  `test_live_span_carries_full_attr_contract`.

- **AC-7 — WIRING.** Driving a real `PlayerActionMessage` / the live
  `_retrieve_entities_for_turn` delegate through the production path emits the
  `retrieval.universal` span WITH `retrieval.card.reason` populated for the selected fill card
  AND publishes a watcher event carrying `embed_skipped` + `card_reasons`. Behavior + span +
  real watcher subscriber only — no source grep. *Test:*
  `test_live_turn_emits_card_reason_span_and_watcher_fields`.

- **AC-8 — Quality gate.** All ACs have failing coverage before GREEN; tree clean; correct
  branch (`feat/84-4-otel-score-decomposition`); `just server-check` green; exactly one
  `retrieval.universal` span per turn (no duplication); telemetry never crashes a turn (the
  emission stays wrapped/swallowed per ADR-006).

## Test Coverage (RED — failing tests in place)
- `sidequest-server/tests/game/test_retrieval_reason_payload.py` — pure helpers
  (`dominant_signal`, `card_reason_payload`): contributions, dominant pick, tie-break,
  JSON-serializability, present-tier. Synthetic `PertinenceScore` fixtures only.
- `sidequest-server/tests/game/test_retrieval_card_reason_span.py` — span-level emission
  (run `-n0`): `retrieval.card.reason` per selected card, empty-list on gate-skip, zero-state
  lifecycle counters, the extended `UNIVERSAL_RETRIEVAL_SPAN_ATTRS` contract + live span carries it.
- `sidequest-server/tests/server/dispatch/test_retrieval_reason_watcher.py` — watcher-event
  fields via the `_capture_publish` spy on `retrieve_for_turn`: `embed_skipped` both polarities,
  `card_reasons` payload.
- `sidequest-server/tests/server/dispatch/test_retrieval_reason_wiring.py` — production WIRING
  through the live `_retrieve_entities_for_turn` delegate (real handler + span exporter + real
  `watcher_hub` subscriber): span `retrieval.card.reason` populated + watcher `embed_skipped` +
  `card_reasons`.

## Notes for Dev
- **The watcher event is the GM-panel reader path**, not the Jaeger span. 84-1 put
  `embed_skipped` on the span only — the dashboard never sees it. The load-bearing WI-6 change
  is extending `server/dispatch/universal_retrieval.retrieve_for_turn`'s published `fields`.
- **OTEL attributes can't hold a list of dicts.** JSON-encode the `retrieval.card.reason` list
  into a single string span attribute. For the watcher event, pass the native list — the hub's
  `_coerce_attr_value` JSON-stringifies it for the synthetic span and the raw event fields
  carry the structured list to the dashboard.
- **No dead lifecycle code.** `tier_demotions`/`rehydrations`/`vectors_shed` are honest `0`s
  this turn; `tier` is the card's one real present tier. Do not add WI-3 demotion functions.
- Consumer path the wiring test exercises:
  `websocket_session_handler.py _retrieve_entities_for_turn`
  → `server/dispatch/universal_retrieval.py retrieve_for_turn` (watcher emit — add fields here)
  → `game/retrieval_orchestration.py retrieve_turn_context` / `_finish` (span emit — add attr here).
- The span-attr contract set lives in `sidequest/game/entity_card.py`
  (`UNIVERSAL_RETRIEVAL_SPAN_ATTRS`); 84-1 did NOT add `retrieval.embed_skipped` to it — WI-6
  closes that gap.

---
_Acceptance criteria authored by TEA (Amos Burton) during the RED phase from ADR-118 §D5 +
Amendment §A5 and the 84-4 session brief. Supersedes the generated placeholder._
