---
parent: "75"
workflow: tdd
---
# Story 75-5 Context — retrieve_turn_context floor+fill orchestration + per-turn token-budget seam (ADR-118)

## Business Context

A living world accretes cast and geography (SOUL: *Living World*, *Diamonds and Coal*). The narrator is fed relevance, not inventory: NPCs and locations present this turn must be included in full detail (the *floor*, from 75-2), while others enter the prompt only if they are semantically similar to the action text (the *fill*, via vector retrieval). Under a single per-turn token budget, this keeps the prompt focused on what is *relevant* rather than what *exists*.

**This is the orchestration layer of ADR-118.** 75-2 delivers the deterministic floor (scene-present entities by recency), 75-4 delivers the indexed cards (EntityCard + typed store), and **75-5 weaves them together**:

1. Assemble the **floor** — via 75-2's selection logic, scene-present NPCs at full detail.
2. Query the **fill** — embed the action text once, semantic top-k over non-floor cards within the remaining budget.
3. Inject into the **Valley zone** — register retrieved NPCs/locations/factions into the prompt as typed sections.
4. **Guard the seam** — a per-turn token-budget fence so retrieval never crowds out the core narrative turn payload.

The narrator is no longer fed the full `npc_pool` blob and every location from the snapshot. Instead, it sees a **budgeted working set**: the present scene in full detail, plus the top-k semantically relevant entities from history, all under a hard token ceiling. Relevance, not existence, governs what the narrator reads.

**Whom it serves:** Sebastien and Jade (mechanics-first) and the whole table benefit when the narrator stays responsive to a dynamic cast rather than reading from a static roster blob. The OTEL spans (below) are a Keith/dev lie-detector — **not** a player-facing surface.

## Technical Guardrails

The canonical, code-level technical approach lives in the **session file** (`.session/75-5-session.md`, higher spec authority than this document). These are the constraints test design must enforce:

- **Repo / language:** `sidequest-server` (Python). Base branch: `develop`. Apply the `python.md` lang-review checklist.
- **Floor + fill, not floor-only:** 75-5 is the orchestration that plugs 75-2's selection (the floor) into a retrieval pipeline. The floor is 75-2's responsibility; 75-5 calls it and wraps the fill around it. A test must prove both the floor and the fill enter the prompt, with the floor always present.
- **One budgeted pass, not two:** the retrieval orchestration is **a single `retrieve_turn_context` function** that takes:
  - The current turn action text (query string for embedding)
  - The current turn context (to extract the floor set)
  - A per-turn token budget (a constant, e.g., 4000 tokens)
  - And returns typed sections: `retrieved_npcs`, `retrieved_locations`, `retrieved_factions` (or empty/None, honoring zero-byte-leak)
  - The lore retrieval continues as a sibling pass with its own budget; per-turn *total* budget is **not** unified in v1 (that is 75-7 instrumentation follow-up). The 75-5 contract is explicit: "this budget is for entities."
- **Prompt-injection sanitization at the assembly choke-point (AC forwarded from 75-4 review):** `EntityCard.content` carries player-influenced fields (NPC/faction names via Yes-And, location descriptions). ADR-047 sanitizes only at the player WebSocket boundary; narrator-context assembly is unsanitized for lore and was unsanitized for entities. **This story must apply `sanitize_player_text` at the retrieval → Valley injection step**, the single choke-point where all retrieved entity content passes before prompt assembly. A test must assert the sanitization fires with a malicious payload (newline, prompt-injection attempt).
- **Dimension-mismatch guard at query time:** when the daemon embedding worker changes dimension (model upgrade), prior EntityCard embeddings become stale. The lore RAG calls `requeue_dimension_mismatched` before every similarity query; the universal index must do the same. A test must verify the guard function is called and re-queues dimension-mismatched cards (span `retrieval.dimension_mismatch_count`).
- **Valley-zone typed injection, zero-byte-leak discipline:** if no entities are retrieved for a type (e.g., no NPCs), the section is not registered to the Valley zone — no empty `retrieved_npcs: []` in the prompt. The Valley is the narrator's *addition*; it does not emit placeholder sections. A test must assert no section registered when the set is empty, and a non-empty set registers its section.
- **OTEL span is mandatory (ADR-118 D5, project OTEL principle):** every narrator turn emits `retrieval.universal` span with:
  - `retrieval.budget_total` (token budget for entities)
  - `retrieval.floor_count`, `retrieval.floor_token_cost` (scene-present breakdown)
  - `retrieval.fill_candidate_count`, `retrieval.fill_selected_count`, `retrieval.fill_token_cost` (semantic top-k breakdown)
  - `retrieval.npc_count`, `retrieval.location_count`, `retrieval.faction_count` (per-type)
  - `retrieval.rejected_below_similarity`, `retrieval.dimension_mismatch_count` (guard metrics)
  - `retrieval.outcome` (`"success"`, `"budget_exhausted"`, `"query_failed"`, `"no_candidates"`)
  - A test must assert the span fires with correct counts for a given scenario.
- **Wired into the live turn-build path (project doctrine):** `retrieve_turn_context` is called from `orchestrator.py:_build_turn_context` (or equivalent production path), not isolated in a test. At least one integration/wiring test must prove retrieved entities flow into the Valley section and reach the narrator prompt through the actual turn-build pipeline, not merely unit-correct in isolation.
- **Meaningful assertions only:** assert the *entity counts, token costs, and injected section structure*, never `assert x is not None` where the value is the real contract.

## Scope Boundaries

**In scope:**
- The `retrieve_turn_context` orchestration function — takes turn context, action text, budget; returns typed sections.
- Floor assembly — calls 75-2's `build_npc_working_set` selection; assembles the full-detail tier.
- Fill pipeline — embedding the action text, querying the entity store by similarity, applying budget + similarity floor.
- Per-turn token budget seam — tracks floor cost first, fills remaining budget with semantic top-k until exhausted.
- Valley-zone injection — registers typed sections (retrieved_npcs / retrieved_locations / retrieved_factions) into `TurnContext`.
- Prompt-injection sanitization at the choke-point — apply `sanitize_player_text` to all retrieved `EntityCard.content` before injection.
- Dimension-mismatch requeue — call `EntityStore.requeue_dimension_mismatched` before all similarity queries.
- OTEL span — emit `retrieval.universal` with all D5 attributes.
- Wiring test — prove the flow reaches the Valley and the prompt through production turn-build.

**Out of scope (do not let tests demand these):**
- **Floor itself** — 75-2 (already merged). 75-5 calls it; it does not re-implement or re-test the floor logic.
- **Retrieval index storage** — 75-4 (already merged). EntityCard + EntityStore exist; 75-5 queries them.
- **Card sync/reproject hook** — 75-6. The index is static for 75-5's purposes; dirty-flag mutation is future.
- **OTEL GM-panel surface** — 75-7. Define and emit the span; the dashboard rendering is separate.
- **Per-turn *total* budget unification (lore + entities)** — 75-7 instrumentation follow-up. Lore and entity retrieval each run under independent budgets in v1.
- **Accretion / lore re-feed** — 75-1 (merged). The lore RAG is live; 75-5 coexists with it.
- **End-to-end action→floor+fill→Valley integration** — 75-8 (after 75-7). 75-5 ships the orchestration; 75-8 proves the full wiring.

## AC Context

The five ACs (verbatim source: session file `## Acceptance Criteria`) and what each demands of test design:

1. **`retrieve_turn_context` orchestration implemented** — generalizes `retrieve_lore_context` into a floor+fill pass:
   - Takes turn context, action text, budget; returns typed sections.
   - Calls 75-2's floor selection; assembles full-detail tier.
   - Embeds action text once; queries entity store by similarity.
   - Budgets floor first, fills remainder with semantic top-k.
   - Tests: `test_retrieve_turn_context_applies_floor_before_fill`, `test_budget_exhausted_stops_fill`, `test_no_candidates_empty_result`.

2. **Floor always present, fill bounded by budget** — the scene-present working set enters the prompt in full; semantic retrieval only populates remaining budget:
   - Tests: floor and fill are separate fields/tiers in the result; floor token cost is counted first; fill cannot exceed `budget − floor_cost`.

3. **Prompt-injection sanitization at the choke-point** — `EntityCard.content` is sanitized before Valley injection:
   - Tests: `test_sanitization_applied_to_retrieved_entity_content` — inject a card with newlines/`<|im_start|>` → asserts sanitization fired and the output is safe.

4. **Dimension-mismatch requeue on query** — before each `query_by_similarity` call, dimension-mismatched embeddings are re-queued:
   - Tests: synthesize a scenario with a stale embedding (wrong dimension), call `retrieve_turn_context`, assert the guard function is called and span `retrieval.dimension_mismatch_count > 0`.

5. **Valley-zone typed injection, zero-byte-leak** — retrieved entities are registered into AttentionZone.Valley as typed sections; empty sets do not register:
   - Tests: `test_empty_entity_set_no_section_registered`, `test_non_empty_entities_registered_to_valley` — call `_build_turn_context`, assert the Valley has the right sections.

**Negative / paranoia cases test design should add (beyond the AC minimum):**
- Floor is empty (no scene-present NPCs) → fill operates on full pool; test passes.
- Budget is exhausted by the floor → fill is empty; no semantic pass runs.
- Query embedding fails (daemon unavailable) → retrieval outcome is `"query_failed"`, empty result, span emitted with failure flag.
- Similarity threshold filters all candidates → outcome `"no_candidates"`, empty result.
- All selected entities are rejected (duplicate floor dedup case) → result deduped, span records the dedup count.
- Per-type counts in the span sum correctly (npc + location + faction = total selected).

## Assumptions

- **75-2 (floor) and 75-4 (EntityCard + store) are merged** — `build_npc_working_set`, the EntityStore, and the embedding machinery are live and callable.
- **The daemon embedding worker is polymorphic** — it consumes both `LoreFragment` and `EntityCard` with `embedding_pending=True`. If this proves false, log a deviation.
- **ADR-118 is the design of record**; this story implements the D4 floor+fill seam exactly.
- **ADR-047 sanitization is available** — import and use `sanitize_player_text` from `protocol.py` or equivalent; it is the choke-point for all narrator-bound text.
- **The lore retrieval continues unchanged** — this story retrieves entities in parallel, not as a replacement for lore. Lore+entities are separate Valley sections.

---
_Authored by Neo (Architect) during SETUP-phase story definition, 2026-06-01.
Sources: ADR-118 (§D4 floor+fill seam, §D5 OTEL), epic-75 context (scout audit), sibling 75-4 context (projectors/store), 75-2 context (floor definition), and the forward-flagged ACs from 75-4 review (sanitization, dimension-mismatch requeue). The session file remains the higher-authority spec; this document is the test-strategy lens the RED phase requires._
