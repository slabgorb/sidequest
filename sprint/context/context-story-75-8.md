---
parent: context-epic-75.md
workflow: tdd
---

# Story 75-8: Universal retrieval — end-to-end integration wiring test (action → floor+fill → Valley injection, ADR-118)

## Business Context

This is the **capstone wiring test** for Epic 75 (ADR-118: Universal Retrieval Layer). Stories 75-1 through 75-7 built and merged the whole pipeline — runtime lore accretion (75-1), budgeted NPC working-set floor (75-2), the EntityCard model + projectors (75-4), `retrieve_turn_context` floor+fill orchestration (75-5), the accretion-triggered card reproject hook (75-6), and the `retrieval.universal` OTEL span (75-7). What does **not** yet exist is a single test that proves the seam is reachable end-to-end **from the real per-turn production path**.

Why this matters: per project doctrine ("Every Test Suite Needs a Wiring Test") and the OTEL Observability Principle, unit tests proving each piece works in isolation are not enough — they don't catch a feature that is built but never *called* from production. ADR-118's value proposition (relevance, not recency-of-existence, governs what the narrator sees; the present scene is never dropped) is only real if the universal-retrieval pass actually runs every turn and its output actually lands in the narrator prompt. This story is the lie detector for the lie detector: it confirms the pipeline is wired, so Keith (and the GM panel) can trust that retrieved NPCs/locations/factions are genuinely being selected and injected rather than the narrator improvising over a snapshot blob.

No new feature behavior ships here — this is a **test-only** story (2 pts). Its outcome is confidence that Epic 75 is integrated, not just assembled.

## Technical Guardrails

**This is a wiring test, not a synthetic fixture.** The single load-bearing risk (named in project memory: "Combat-mutation features must wire BOTH resolution paths" / "Drive the real pack, not a synthetic fixture") is that the test constructs `retrieve_turn_context()` directly, asserts on its return value, and proves *nothing* about whether production ever calls it. **A direct `retrieve_turn_context()` call is the #1 no-op trap.** The test MUST enter through the production delegate.

**Production seams the test must touch** (from Architect/Leonard investigation, see `.session/75-8-tandem-architect.md` for full file:line map):

- **Per-turn entry:** `handler._retrieve_entities_for_turn(sd, action)` — `websocket_session_handler.py:2986` → `dispatch/universal_retrieval.py:retrieve_for_turn` (≈:46) → `retrieve_turn_context` (≈:159). Live callers: `player_action.py:496` (main turn) and `websocket_session_handler.py:2500` (opening turn). Drive the delegate, not the orchestration function.
- **Floor + fill orchestration:** `retrieval_orchestration.py` — floor is the 75-2 working-set selection (scene-present: `last_seen ≤ N`, with the turn-1/2 guard `last_seen_turn > 0` from 75-2's review); **floor entities are deduped OUT of the fill candidate set** (≈`retrieval_orchestration.py:268`). Fill = embed(action) once → cosine top-k over non-floor cards → fill remaining budget (budget − floor_cost) under a similarity floor.
- **Valley injection (75-8's net-new assertion surface):** `_build_turn_context` → `render_entity_section` (`session_helpers.py:1144-1156`) → `registry.register_section(..., AttentionZone.Valley, ...)` (`orchestrator.py:2137-2156`). Typed sections: `retrieved_npcs` / `retrieved_locations` / `retrieved_factions`.
- **EntityCard projectors (75-4):** module functions `project_npc_card` / `project_location_card` / `project_faction_card` — **there is NO `to_card()` method** (correct any spec text that says so). `content` is an embeddable text projection, not a raw data dump.
- **OTEL span (75-7):** `retrieval.universal` with attributes `retrieval.budget_total`, `retrieval.floor_count`, `retrieval.floor_token_cost`, `retrieval.fill_candidate_count`, `retrieval.fill_selected_count`, `retrieval.fill_token_cost`, per-type `retrieval.{npc,location,faction}_count`, `retrieval.rejected_below_similarity`, `retrieval.dimension_mismatch_count`, and a distinct `retrieval.outcome` per failure mode.

**Model after:** `tests/server/dispatch/test_universal_retrieval_dispatch.py`. Keep the new test in `tests/server/dispatch/` to dodge the PG / `SIDEQUEST_GENRE_PACKS` env gotchas. Use `session_handler_factory` (MagicMock repo, no Postgres), a fake `embed()` returning a fixed vector (`query_by_similarity` is pure cosine — fully offline, no daemon/MiniLM needed, no flag-gate to enable), and `InMemorySpanExporter` for the span assertion.

**Banned:** source-text/regex wiring tests are prohibited by `sidequest-server/CLAUDE.md` (cf. memory: "Replace source-text wiring test"). Assert behavior (sections registered, span fired, watcher event reached the hub), not strings in source.

## Scope Boundaries

**In scope:**
- One integration/wiring test in `tests/server/dispatch/` that drives a real turn through `handler._retrieve_entities_for_turn` and asserts the full arc in a single test: (a) `retrieve_turn_context` was reached via the production delegate, (b) floor entities (scene-present) are present full-detail, (c) semantically-relevant non-floor cards are filled under budget, (d) retrieved cards register as typed Valley `PromptSection`s, (e) zero-byte-leak (a type that retrieved nothing registers NO section), (f) the `retrieval.universal` span fired with sane attributes.
- Correcting any AC phrasing that references a non-existent `to_card()` method → use the `project_*_card` module functions.

**Out of scope:**
- Any change to retrieval behavior, budgets, projectors, or the span (those shipped in 75-4..75-7). This story adds a test only; if the test reveals a real wiring gap, log it as a Delivery Finding and raise to SM rather than silently fixing scope into this story.
- Budget/similarity-floor calibration tuning (ADR-118 flags this for playtest, not this story).
- Location-source consolidation, PG promotion of the index, inventory/event card types (all ADR-118 future work).
- The GM-panel dashboard surface (delivered by 75-7).

## AC Context

The 8 ACs in the session file collapse into one end-to-end arc. Testable detail per AC:

1. **Full-pipeline reachability** — assert the call traces from `handler._retrieve_entities_for_turn` (production delegate), NOT a direct `retrieve_turn_context()` construction. Edge: if entered the wrong way the test passes while production is dead — guard by entering via the handler delegate and asserting a Valley section landed downstream.
2. **Floor guarantee** — seed ≥1 scene-present NPC (`last_seen_turn > 0`, within N turns) with deliberately LOW similarity to the action text; assert it is still in the retrieved set, full detail. Edge: turns 1–2 (the 75-2 guard) — a default `last_seen_turn = 0` NPC must NOT be misclassified scene-present.
3. **Semantic fill** — seed non-scene-present cards in `sd.entity_store`; one semantically near the action text, one far. Assert near is filled, far is rejected below `DEFAULT_RETRIEVAL_MIN_SIMILARITY`.
4. **Budget enforcement** — assert floor+fill token total ≤ per-turn budget (default 4000, top_k 8); seed short non-scene-present fill cards so budget math doesn't drop them for the wrong reason. Edge: budget exhausted before fill → distinct `outcome`, not a crash.
5. **Type-tagged injection + zero-byte-leak** — assert `retrieved_npcs`/`retrieved_locations`/`retrieved_factions` register as separate Valley sections; assert a type that retrieved nothing registers NO section (`if section_body:` guard, None-list contract) — not an empty tag.
6. **OTEL observability** — `InMemorySpanExporter`; assert `retrieval.universal` fired with floor_count, fill counts/tokens, per-type counts, similarity-floor rejections, and a success `outcome`. (75-7 already asserts the span+watcher event; 75-8 pins it as part of the same end-to-end arc alongside the Valley assertion.)
7. **Projectors reachable** — assert `project_npc_card`/`project_location_card`/`project_faction_card` run on the retrieval path and produce embeddable `content` (not a verbatim struct dump). NO `to_card()` method.
8. **Integration test passes** — the real-turn scenario asserts the retrieved set contains the expected NPCs/locations/factions AND that the prompt does not carry a full `npc_pool` blob for the retrieved-NPC channel (ADR-118 supersedes ADR-059's every-turn full-blob carry).

**Floor-dedup trap (must-heed):** because the floor is deduped out of the fill candidate set (`retrieval_orchestration.py:268`), fill candidates must be seeded as entities that are NOT scene-present, or the fill silently no-ops and the test proves nothing about semantic retrieval.

## Assumptions

- **75-1..75-7 are merged** on `sidequest-server/develop` and the branch is cut from current develop (verified: branch off `baff0ae4`, #594). Dependency 75-7 merged via #342.
- **Offline-testable:** `query_by_similarity` is pure cosine, so a fake `embed()` returning a fixed vector removes the daemon/MiniLM dependency — no network, no GPU, CI-safe.
- **No flag/config gate** enables universal retrieval; it runs on the standard per-turn path. (If TEA finds a gate, that's a Delivery Finding.)
- **The pipeline is actually wired.** If the wiring test cannot reach `retrieve_turn_context` from the production delegate without modifying production code, that is a genuine integration gap from 75-5/75-6 — log it as a blocking Delivery Finding and raise to SM; do not paper over it by calling the orchestration function directly.
