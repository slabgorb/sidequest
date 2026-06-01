---
story_id: "75-5"
jira_key: ""
epic: "75"
workflow: "tdd"
---
# Story 75-5: Universal retrieval: retrieve_turn_context floor+fill orchestration + per-turn token-budget seam (ADR-118)

## Story Details

- **ID:** 75-5
- **Epic:** 75 — RAG Retrieval Layer
- **Points:** 5
- **Priority:** p2
- **Jira Key:** (none — this is a personal project)
- **Workflow:** tdd
- **Stack Parent:** 75-4 (EntityCard + per-type projectors + typed store)
- **Depends On:** 75-4 ✓ (done 2026-06-01)
- **Unlocks:** 75-6 (card sync/reproject hook), 75-7 (OTEL instrumentation + GM-panel)

## Acceptance Criteria

1. **`retrieve_turn_context` orchestration implemented** — generalizes `retrieve_lore_context` into a floor+fill retrieval pass:
   - Takes turn context, action text, and a per-turn token budget for entities (e.g., 4000 tokens)
   - Calls 75-2's `build_npc_working_set` to assemble the floor (scene-present NPCs at full detail)
   - Embeds the action text once via the daemon embedding worker (reuses existing lore machinery)
   - Queries the EntityStore by semantic similarity over non-floor cards
   - Applies a similarity threshold (cf. `DEFAULT_RETRIEVAL_MIN_SIMILARITY`, mirroring lore retrieval)
   - Budgets the floor cost first, fills the remaining budget with semantic top-k until exhausted
   - Returns typed sections: `retrieved_npcs`, `retrieved_locations`, `retrieved_factions` (or None if empty)

2. **Floor always present, fill bounded by budget** — the scene-present working set enters the prompt in full; semantic fill only consumes the remaining budget:
   - Floor token cost is counted first; fill cannot exceed `budget − floor_cost`
   - Floor and fill are tracked separately in the OTEL span (see AC-4)
   - A test must prove both tiers appear in the result under a budgeted scenario

3. **Prompt-injection sanitization at the choke-point** — all retrieved `EntityCard.content` is sanitized via `sanitize_player_text` (ADR-047) before Valley injection:
   - Content flows from player-influenced fields (NPC/faction names via Yes-And, location descriptions)
   - ADR-047 only sanitizes at the player WebSocket boundary, not narrator-context assembly
   - 75-5 applies sanitization at the retrieval → Valley injection step (the single choke-point)
   - A test must verify sanitization fires with a malicious payload (e.g., embedded newline, `<|im_start|>`)

4. **Dimension-mismatch requeue on query** — before each `query_by_similarity` call, dimension-mismatched embeddings are marked for re-embedding:
   - Calls `EntityStore.requeue_dimension_mismatched` before similarity queries (same guard as `LoreStore`)
   - Tracks the requeue count in the OTEL span as `retrieval.dimension_mismatch_count`
   - A test must verify the guard fires when a card has a stale embedding (wrong vector dimension)

5. **Valley-zone typed injection, zero-byte-leak discipline** — retrieved entities are registered into AttentionZone.Valley as typed sections; empty sets do not register:
   - Wires `retrieve_turn_context` into `orchestrator.py:_build_turn_context` (or equivalent production path)
   - Registers non-empty typed sections: `retrieved_npcs`, `retrieved_locations`, `retrieved_factions`
   - Does not register sections for empty entity sets (zero-byte-leak: no `retrieved_npcs: []` in the prompt)
   - A test must prove the section structure is correct and empty sets are omitted
   - Integration/wiring test: call `_build_turn_context`, assert retrieved entities appear in the Valley zone

6. **OTEL observability span emitted** — every narrator turn fires `retrieval.universal` span with ADR-118 D5 attributes:
   - `retrieval.budget_total` — token budget for entities (e.g., 4000)
   - `retrieval.floor_count` — number of floor entities (scene-present)
   - `retrieval.floor_token_cost` — tokens consumed by floor
   - `retrieval.fill_candidate_count` — total candidate entities for fill
   - `retrieval.fill_selected_count` — entities selected from fill
   - `retrieval.fill_token_cost` — tokens consumed by fill
   - `retrieval.npc_count`, `retrieval.location_count`, `retrieval.faction_count` — per-type breakdown
   - `retrieval.rejected_below_similarity` — candidates rejected due to similarity threshold
   - `retrieval.dimension_mismatch_count` — embeddings re-queued due to dimension mismatch
   - `retrieval.outcome` — success status (`"success"`, `"budget_exhausted"`, `"query_failed"`, `"no_candidates"`)
   - A test must assert the span fires with correct counts for a given scenario

## Technical Approach

### File Structure

The implementation adds/modifies:

- **`sidequest/game/retrieval_orchestration.py`** (new) — core orchestration:
  - `retrieve_turn_context(turn_context, action_text, budget_tokens)` — main function
    - Assembles the floor via 75-2's `build_npc_working_set`
    - Calls the daemon embedding worker to embed the action text
    - Queries the entity store by similarity (`query_by_similarity`)
    - Applies budget constraints and similarity thresholds
    - Returns typed sections (`retrieved_npcs`, `retrieved_locations`, `retrieved_factions`)
  - Helper: `_apply_prompt_injection_sanitization(entity_cards)` — sanitizes all card content
  - Helper: `_dedupe_floor_and_fill(floor_npcs, fill_npcs)` — removes fill duplicates that already appeared in floor
  - OTEL span registration via `WatcherHub` with all D5 attributes

- **`sidequest/orchestrator.py`** (modified) — wires retrieval into `_build_turn_context`:
  - Call `retrieve_turn_context(...)` after the lore retrieval
  - Register typed sections into `AttentionZone.Valley` (zero-byte-leak discipline)
  - Pass the entity sections into the narrator prompt

- **Tests** — `tests/game/test_retrieval_orchestration.py`:
  - Unit: floor assembly, fill pipeline, budget exhaustion, similarity threshold, dimension-mismatch guard, sanitization
  - Integration: synthesize a scenario with NPCs/locations/factions, call `_build_turn_context`, assert sections in the Valley
  - OTEL: verify span fires with correct attributes

### Reuse Points

1. **Floor assembly** — 75-2's `build_npc_working_set(npcs, current_turn, player_referenced_npc)` already selects the floor; call it directly.

2. **Embedding machinery** — `lore_embedding.py:embed_query_text(text)` (or equivalent) embeds action text via the daemon. Reuse the existing path.

3. **Similarity query** — `EntityStore.query_by_similarity(embedding, top_k, entity_type_filter)` already ranks by cosine. Reuse it.

4. **Token estimation** — `lore_store._estimate_tokens(text)` estimates card content length. Reuse for budget tracking.

5. **Sanitization** — `protocol.sanitize_player_text(text)` (or `handlers.sanitize_player_text`) is the existing choke-point. Import and apply at card-content assembly.

6. **OTEL watcher** — `WatcherHub.get_current()` registers spans; emit `retrieval.universal` alongside the existing `lore.*` spans.

### Design Decisions

1. **One budgeted pass per turn** — `retrieve_turn_context` is a single call that handles floor+fill under one token budget. It does not replace the lore retrieval; they run in parallel, each with independent budgets (unifying budgets is 75-7 follow-up).

2. **Floor deduplication** — if an NPC appears in both the floor (scene-present) and the fill (semantic), include it only once (in full detail, from the floor). A helper dedupes fill entities.

3. **Budget is hard** — if fill candidates exceed the remaining budget, they are rejected (not partially encoded). The span records `retrieval.outcome = "budget_exhausted"` when this happens.

4. **Similarity threshold is consistent** — apply the same `DEFAULT_RETRIEVAL_MIN_SIMILARITY` that lore uses, so entity retrieval has the same recall discipline.

5. **Dimension-mismatch guard is pre-query** — before every `query_by_similarity` call, call `EntityStore.requeue_dimension_mismatched(expected_dim)` to re-queue stale embeddings. This mirrors the lore RAG guard (ADR-048 / ADR-118 D5).

### Implementation Order

1. Define `retrieve_turn_context` signature and OTEL span structure
2. Implement floor assembly (call 75-2's selection)
3. Implement fill pipeline (embed → query → budget → sanitize → dedupe)
4. Implement Valley-zone injection (wiring into `_build_turn_context`)
5. Write unit tests for each stage
6. Write integration/wiring test from a real game context
7. Verify OTEL span emissions

## Upstream Findings

- **Lore retrieval is live and fires every turn** — `websocket_session_handler.py:2456 → _retrieve_lore_for_turn()`. This story coexists with it; does not replace it.
- **EntityStore is ready** — 75-4 ships it; embeddings are pending until the daemon drains them.
- **Floor selection is ready** — 75-2 ships `build_npc_working_set`; this story calls it.
- **Sanitization path exists** — `sanitize_player_text` is available; apply it at the retrieval → injection step.
- **OTEL is instrumented for lore** — `lore.*` spans already fire; this story adds `retrieval.universal` as a sibling.

## Forward-Flagged ACs from 75-4 Review

The Reviewer (round-1) and Dev (implementation) of 75-4 surface these constraints for 75-5's acceptance criteria:

- **AC: Prompt-injection sanitization of `EntityCard.content` at the narrator prompt-assembly choke-point** (Reviewer, 75-4 review):
  - ADR-047 `sanitize_player_text` only fires at the player WS boundary, not on narrator-context assembly
  - Content carries player-influenced fields (Yes-And for NPCs/factions, location descriptions)
  - 75-5 must apply sanitization at the retrieval → Valley injection step (the single choke-point where all entity content passes before the prompt)
  - Test: `test_sanitization_applied_to_retrieved_entity_content` — inject a card with newlines/`<|im_start|>`, assert sanitization fires and output is safe

- **AC: When wiring the live daemon embedding worker, add EntityStore equivalents of `LoreStore.requeue_dimension_mismatched` / `mark_embedding_failed`** (Dev Delivery Findings, 75-4):
  - Model upgrades change vector dimension → silent 0.0 scores if unguarded
  - The lore RAG calls `requeue_dimension_mismatched` before every `query_by_similarity` (ADR-048)
  - EntityStore must have the same guard (75-4 omitted it as out-of-scope; 75-5 wires it when queries run)
  - Span `retrieval.dimension_mismatch_count` is reserved in `UNIVERSAL_RETRIEVAL_SPAN_ATTRS`
  - Test: dimension-mismatch guard is called on every `retrieve_turn_context` call with a dimension-mismatched card in the store

## Deviations

None yet. Check back after RED phase.

## Sm Assessment

**Setup verdict:** Ready for RED. Story is the orchestration glue between 75-2's floor, 75-4's index, and the narrator prompt.

- **Dependency gate cleared.** 75-5 depends on 75-4 and transitively 75-2, all done. Nothing blocks the start.
- **Scope boundary is clean.** 75-5 is orchestration + injection only — no new index, no new floor logic, no new projectors. Tests should cover the retrieval pipeline, budget constraints, sanitization, dimension-mismatch guard, and Valley wiring — not the floor logic or card projection (those are 75-2 and 75-4).
- **Reuse over reinvention.** Upstream findings confirm `build_npc_working_set`, EntityStore, embedding worker, and sanitization paths are all live. 75-5 calls them; does not rebuild.
- **Wiring-test requirement.** Per project doctrine, the suite needs at least one integration test proving the orchestrated retrieval reaches the Valley and the narrator prompt through the actual turn-build pipeline.
- **Forward-flagged ACs.** Two constraints bubble up from 75-4 review — sanitization and dimension-mismatch guard — both are explicit ACs here (AC-3 and AC-4).
- **Single repo.** sidequest-server only; branch `feat/75-5-retrieve-turn-context-floor-fill` created and clean.

Handoff to The Architect (TEA) for RED.

## TEA Assessment

**Tests Required:** Yes
**Reason:** 5-pt orchestration story with six ACs, security (sanitization), and a graceful-degradation seam — full TDD coverage required.

**Test Files:**
- `sidequest-server/tests/game/test_retrieval_orchestration.py` — 19 tests across 9 classes covering all six ACs + paranoia cases + wiring.

**Tests Written:** 19 tests covering 6 ACs
**Status:** RED (failing — ready for Dev). Verified via testing-runner (`75-5-tea-red`, read-only):
- 17 × `ModuleNotFoundError` (net-new `sidequest.game.retrieval_orchestration` absent)
- 1 × `AttributeError` (`EntityStore.requeue_dimension_mismatched` absent — AC-4 forces it)
- 1 × `AssertionError` (`_SessionData.entity_store` field absent — AC-5 wiring seam)
- Collection succeeded (19 items); all EXISTING-symbol imports verified clean (no test-side typos).

**AC → test map:**
| AC | Tests |
|----|-------|
| AC-1 orchestration | `TestRetrievalContractSurface::*`, `TestFloorAndFill::test_floor_and_fill_both_present_under_budget` |
| AC-2 floor-first/fill-bounded | `test_floor_token_cost_counted_before_fill`, `test_empty_floor_lets_fill_use_full_budget` |
| AC-3 sanitization choke-point | `TestSanitizationChokePoint::test_malicious_card_content_is_sanitized_before_injection`, `…does_not_mutate_the_stored_card` |
| AC-4 dimension-mismatch requeue | `TestDimensionMismatchGuard::test_entity_store_has_requeue_method_mirroring_lore`, `…requeues_dimension_mismatched_card_and_counts_it` |
| AC-5 Valley zero-byte-leak + wiring | `TestZeroByteLeak::*`, `TestEntityStoreSessionWiring::test_session_data_has_entity_store_field`, `TestRetrievalPipelineWiring::test_player_action_drives_universal_retrieval` |
| AC-6 OTEL span | `TestOtelSpan::test_span_fires_with_all_d5_attributes`, `…per_type_counts_sum_to_fill_selected`, `…records_query_failed_outcome` |

### Rule Coverage (python.md lang-review)

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 Silent exception swallowing | `test_daemon_embed_exception_is_caught_not_propagated`, `test_span_records_query_failed_outcome` (failure RECORDED in `outcome`/span, never silently swallowed) | failing |
| #8/#11 Injection / input validation at boundary | `test_malicious_card_content_is_sanitized_before_injection` (sanitize at the retrieval→Valley choke-point) | failing |
| #2 Mutable default arguments | contract pins `player_referenced_npcs: set[str] | None = None` (not `set()`) | pinned in contract |
| #3 Type annotations at boundary | the pinned public signature is fully annotated (params + `-> RetrievedEntities`) | pinned in contract |
| #6 Test quality | self-check pass — every test asserts specific values (ids, counts, outcomes, content membership); no `assert True`, no truthy-only checks, no skips | clean |

**Rules checked:** 5 of 13 lang-review rules are AC-relevant and have coverage (or are pinned by the contract); the rest (#5 path, #7 resource leaks, #9 async pitfalls, #12 deps) apply at Dev implementation time, not test design.
**Self-check:** 0 vacuous tests written.

**Wiring test:** `TestRetrievalPipelineWiring` drives a real `PlayerActionMessage` through `WebSocketSessionHandler` and asserts the `retrieval.universal` span fired AND a seeded entity reached the narrator prompt — behavior + span, not a source grep (server CLAUDE.md "No Source-Text Wiring Tests"). Plus the sanctioned reflection tripwire on `_SessionData.entity_store`.

**Handoff:** To Agent Smith (Dev) for GREEN. See `## Delivery Findings` for the double-injection Question (floor must not be registered twice) and the 75-6 boundary on store population / `mark_embedding_failed`.

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** 19/19 target GREEN; 33/33 sibling regression GREEN (52 total, 0 fail, 0 skip) — verified via testing-runner (`75-5-dev-green`, read-only, serial `-n0`).

**Files Changed (sidequest-server):**
- `sidequest/game/retrieval_orchestration.py` *(new)* — `retrieve_turn_context` floor+fill orchestration, `RetrievedEntities` result, `SPAN_UNIVERSAL_RETRIEVAL`, `DEFAULT_ENTITY_BUDGET_TOKENS`, `render_entity_section`, and the `_floor_token_cost` / `_floor_card_ids` / `_sanitize_card` helpers. Never raises; emits the `retrieval.universal` span with all 12 ADR-118 §D5 attributes.
- `sidequest/game/entity_store.py` — added `requeue_dimension_mismatched(current_dim)`, mirroring `LoreStore` (AC-4; 75-4 had omitted it).
- `sidequest/server/session_state.py` — added `_SessionData.entity_store: EntityStore` (default-factory), sibling of `lore_store`.
- `sidequest/agents/orchestrator.py` — `TurnContext` gains `retrieved_entity_{npcs,locations,factions}`; `build_narrator_prompt` registers each non-empty block into `AttentionZone.Valley` (zero-byte-leak), beside the lore block. Floor NOT re-registered (no double-injection).
- `sidequest/server/session_helpers.py` — `_build_turn_context` gains `entity_retrieval` param; renders the fill into the typed Valley blocks.
- `sidequest/server/websocket_session_handler.py` — new `_retrieve_entities_for_turn` method; wired into the opening-turn path.
- `sidequest/handlers/player_action.py` — wired entity retrieval into the player-action turn (the path the wiring test drives).

**Quality gate:** ruff check ✓, ruff format ✓, pyright introduces **0 new errors** (new module 0; every edited file's count equals its HEAD baseline — orchestrator 1=1, player_action 20=20, handler 25=25 are pre-existing `develop` debt, out of scope per minimalist discipline).

**Self-review:**
- ✅ Wired end-to-end: handler → `retrieve_turn_context` → `TurnContext` → Valley section → narrator prompt (proven by `TestRetrievalPipelineWiring`, behavior + span).
- ✅ Follows the live `retrieve_lore_context` sibling pattern (async, daemon seam, never-raises, span-recorded outcomes).
- ✅ All 6 ACs met; AC-3 sanitization at the choke-point without mutating the store; AC-4 guard mirrors LoreStore; AC-5 zero-byte-leak honored at both data and prompt level.
- ✅ Error handling: daemon failure → recorded `query_failed` outcome + span (No Silent Fallbacks), never a swallowed empty success.

**Branch:** `feat/75-5-retrieve-turn-context-floor-fill` (sidequest-server, pushed)
**Handoff:** To The Merovingian (Reviewer). See `## Delivery Findings` → Dev for the 75-6 store-population boundary and the double-`build_npc_working_set` improvement.

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected (1 minor mismatch; all 6 ACs substantively met)
**Structural gate:** PASS — AC coverage, implementation-complete flag, and TEA+Dev deviation subsections all present.
**Mismatches Found:** 1

- **AC-6 "every narrator turn fires `retrieval.universal`" — the MP crash-release path emits no span** (Missing in code — Behavioral, Minor)
  - Spec: AC-6 — "every narrator turn fires `retrieval.universal` span."
  - Code: the four narrator-turn entry points are opening (`_run_opening_turn_narration`, wired), single-player action (`player_action.handle` → 498 build, wired), and MP barrier-fire (`dispatch_fired_barrier`, inherits the entity-enriched `turn_context` from the 498 build — wired). The fourth, the Story 67-1 MP **crash-release** path (`client_error.py:128`), builds its own `turn_context` with `lore_context=None` and no `entity_retrieval`, so `retrieve_turn_context` is never called and no span fires on that turn.
  - Recommendation: **D — Defer.** The crash-release path *intentionally* skips per-action retrieval (its own comment: `lore_context=None` because "the dispatched action is the combined pending buffer … not a single action we could retrieve lore for here"). The entity-retrieval absence therefore exactly mirrors the existing lore behavior on the identical path — consistent, not a regression. The floor is still built (via `_build_turn_context`); only the per-action fill + span are skipped, on an MP edge path where retrieval is a deliberate no-op. Forcing a span here would observe nothing. A future story (or 75-7, which owns the dashboard surface) may emit a minimal `outcome="no_candidates"` span here if crash-release OTEL coverage is later deemed necessary.

**Alignment confirmed on the rest:**
- AC-1/AC-2/AC-3/AC-4/AC-5 — substantively met; proven by the 19-test GREEN suite incl. the behavior+span wiring test.
- The `retrieve_turn_context` signature refinement and the double-`build_npc_working_set` call are already logged as TEA/Dev deviations (Option A — accepted; the floor call is required by the unit contract).
- AC-6's dashboard watcher event (the lore path's sibling `lore_retrieval` publish) is correctly **absent** — the GM-panel surface is explicitly 75-7 scope. The OTEL span (the lie-detector data) is present, which is what AC-6 requires.
- No-double-injection confirmed: the floor rides `npc_working_set`; only the fill registers new Valley sections.

**Decision:** Proceed to review. The single mismatch is Minor, internal, consistent with the sibling lore path, and recommended for Defer — it does not warrant a hand-back to Dev. The Merovingian should weigh the crash-release coverage gap and confirm the Defer.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (52/52 from green phase; working tree unchanged this phase)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 7 (diff vs `develop`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | Intentional lore-sibling parallelism confirmed by-design (ADR-118 "Don't Reinvent"); shared `cosine_similarity` / `_estimate_tokens` / `sanitize_player_text` already reused. No genuine duplication. |
| simplify-quality | 3 findings (all low) | All self-annotated "no action needed / consistent with conventions": local-var init pattern (safe), inline render-wiring asymmetry (correct ownership split), Valley loop idiom (matches lore registration above). Type annotations, no mutable defaults, no dead code, OTEL coverage all ✓. |
| simplify-efficiency | 1 finding (medium) | Valley registration loop (orchestrator.py) could use a dict instead of a tuple-of-tuples. |

**Applied:** 0 high-confidence fixes (none surfaced).
**Flagged for Review:** 1 medium (Valley loop dict-vs-tuple) — NOT applied. Rationale: it is a lateral stylistic swap, not an improvement; the code is already a single loop (not three repeated blocks as the finding's "15→8 lines" implies) and deliberately mirrors the `retrieved_lore` registration immediately above it. A dict would obscure the intentional npc→location→faction ordering. simplify-quality independently judged this pattern "consistent with project conventions, no change needed."
**Noted:** 3 low (stylistic observations, no action).
**Reverted:** 0 (no changes applied → no regression risk → revert/recheck skipped per verify-workflow Step 7).

**Overall:** simplify: clean (no high-confidence fixes; 1 medium + 3 low flagged, none actionable)

**Quality Checks:** ruff check ✓ (changed files), ruff format ✓, pyright 0 new errors (green phase), 52/52 tests GREEN (green phase) — code byte-identical since, nothing applied this phase.
**Handoff:** To The Merovingian (Reviewer). The Architect (spec-check) flagged one Minor deferred mismatch (MP crash-release path emits no `retrieval.universal` span, consistent with its existing lore-skip) for the Reviewer to confirm.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — tests GREEN (19+33), ruff pass, pyright 0-new, 0 actionable smells |
| 2 | reviewer-edge-hunter | Yes | findings | 11 | confirmed 3 (medium/low, span-accounting), dismissed 8 (incl. both HIGH never-raises — mitigated at daemon boundary) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 1 | confirmed 1 (medium — error_type/error_code not on span) |
| 4 | reviewer-test-analyzer | Yes | findings | 8 | confirmed 3 (medium test-hardening/coverage), dismissed/noted 5 (low) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings (rule-by-rule done by Reviewer below) |
| 7 | reviewer-security | Yes | findings | 2 | confirmed 2 (both pre-existing/underlying-sanitizer — out of 75-5 scope, follow-up filed) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings (verify-phase simplify already ran clean) |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings (rule-by-rule done by Reviewer below) |

**All received:** Yes (5 enabled returned; 4 disabled via settings)
**Total findings:** 9 confirmed (all Medium/Low, non-blocking), 8 dismissed (with rationale), 0 deferred-blocking

### Key adjudications

- **DISMISS [EDGE] HIGH `response["embedding"]` KeyError + zero-length "never-raises violation"** — evidence: `DaemonClient.embed` (client.py:156-174) catches `KeyError` → `DaemonRequestError("INVALID_RESPONSE")`, refuses non-list / **zero-length** / non-numeric replies as `DaemonRequestError`. That type is in `retrieve_turn_context`'s `except` clause, so no raw exception escapes; `len(query_embedding)` is always ≥1 downstream. `EmbedResponse` is a `TypedDict` (runtime dict) so `response["embedding"]` is valid. This mirrors the live `retrieve_lore_context` sibling exactly. The silent-failure-hunter independently verified this mitigation.
- **DISMISS [EDGE] MEDIUM `sanitize_player_text` could raise** — it operates on a pydantic-validated non-empty `str` and performs only regex subs + `.strip()`; no raise path for `str` input.
- **DISMISS [EDGE] LOW** mutation-during-iteration in `requeue_dimension_mismatched`, `token_estimate==0`, unknown `entity_type` in `_finish` — the requeue mirrors the live `LoreStore` exactly; `_estimate_tokens` is `(len+3)//4 ≥ 1` for validated non-blank content; `EntityCard.new` enforces `entity_type ∈ _ID_NAMESPACE` (the only construction path the projectors use).

## Rule Compliance

Rule-by-rule enumeration (type_design + rule_checker disabled → done here by the Reviewer) against `python.md` lang-review + CLAUDE.md/SOUL.md:

- **#1 No silent exception swallowing / No Silent Fallbacks** — `retrieve_turn_context` catches `(DaemonUnavailableError, DaemonRequestError, ValueError)`, logs at WARNING, and records `outcome="query_failed"` on the span. **Compliant** (failure recorded, not swallowed) — see finding R1 for the sibling-parity granularity gap.
- **#2 Mutable default args** — `player_referenced_npcs: set[str] | None = None`, `client: DaemonClient | None = None`; `_SessionData.entity_store = field(default_factory=EntityStore)`. **Compliant** (no shared mutable defaults).
- **#3 Type annotations at boundaries** — `retrieve_turn_context`, `RetrievedEntities`, `requeue_dimension_mismatched`, `render_entity_section`, `_retrieve_entities_for_turn` all fully annotated. **Compliant**.
- **#4 Logging correctness** — WARNING on degraded paths, lazy `%s` format. **Compliant**.
- **#6 Test quality** — no vacuous assertions; tests assert ids/counts/outcomes; wiring test is behavior+span (not source-grep); reflection tripwire is the sanctioned exception. **Compliant** — findings R4-R6 are hardening, not violations.
- **#8/#11 Injection / input validation at boundary (ADR-047)** — AC-3 fill path: every selected `EntityCard.content` passes `_sanitize_card`→`sanitize_player_text` before reaching the prompt; store not mutated (`model_copy`). **Compliant for the fill (75-5's surface).** The floor path and the chatml-token sanitizer gap are pre-existing/underlying — findings R2/R3, out of 75-5 scope.
- **No double-injection** — floor rides `npc_working_set`; orchestrator registers only the non-empty fill sections. **Compliant** (verified orchestrator.py registration loop).
- **Every Test Suite Needs a Wiring Test** — `TestRetrievalPipelineWiring` drives the real handler, asserts span + prompt content. **Compliant**.

## Devil's Advocate

Argue this code is broken. **The narrator crashes mid-turn.** If the daemon returns a reply my `except` clause doesn't anticipate, `retrieve_turn_context` raises and kills the turn. — *Refuted:* `DaemonClient.embed` is the sole boundary and it normalizes every malformed/empty/non-numeric reply to `DaemonRequestError`, which is caught; `EmbedResponse` is a TypedDict so subscripting is safe. The live lore sibling has relied on this exact contract in production.

**A player jailbreaks the narrator.** A malicious Yes-And NPC name reaches the prompt unsanitized. — *Partially upheld:* the **fill** (EntityCard.content) is sanitized, but the **floor** (npc_roster) is not, and `sanitize_player_text` misses chatml `<|im_start|>` tokens. Both are real (findings R2/R3) — but neither is *introduced* by this diff: the floor path predates 75-5 and is unchanged, and 75-5 correctly calls the ADR-047 sanitizer that AC-3 names. The default Anthropic narrator does not parse chatml delimiters; the exposure is the Ollama opt-in backend. Filed as follow-ups, not 75-5 regressions.

**The GM panel lies about retrieval.** On a `query_failed` turn the operator can't tell daemon-down from model-fail — the span omits `error_type`/`error_code` the lore sibling records (finding R1). And `rejected_below_similarity` undercounts (top_k-truncated and floor-deduped candidates vanish from the counters). — *Upheld as Medium:* these are genuine observability-granularity gaps. But the **required** AC-6 attribute set (the 12 in `UNIVERSAL_RETRIEVAL_SPAN_ATTRS`) is fully emitted with correct values, the per-type sum invariant holds (tested), and `outcome` is always recorded. The lie-detector fires; it is merely less granular than its sibling. Non-blocking; routed to 75-7 (which owns the OTEL/dashboard polish).

**A confused state corrupts the store.** `requeue_dimension_mismatched` mutates cards while iterating. — *Refuted:* it mutates values, not dict structure (CPython-safe), and is a line-for-line mirror of the live `LoreStore` method. Net: no broken-in-this-diff behavior; the real exposures are pre-existing security gaps now explicitly tracked.

## Reviewer Assessment

**Verdict:** APPROVED

**Observations:**
- `[VERIFIED]` Never-raises contract holds — `retrieve_turn_context` catches all daemon-reply failure classes via the `DaemonClient.embed` boundary (client.py:156-174 normalizes to `DaemonRequestError`); evidence: retrieval_orchestration.py:238-254 except clause + the TypedDict return. Mirrors the live lore sibling.
- `[VERIFIED]` AC-3 fill sanitization at the choke-point — every selected card is `_sanitize_card`'d (model_copy, store untouched) before `render_entity_section` → Valley; evidence: retrieval_orchestration.py:284-285 + `test_sanitization_does_not_mutate_the_stored_card`. Complies with ADR-047 for the fill surface.
- `[VERIFIED]` No double-injection — floor rides `npc_working_set`; orchestrator.py registers only non-empty `retrieved_entity_*` fill blocks into Valley; evidence: the registration loop + session_helpers render block.
- `[VERIFIED]` AC-4 guard mirrors LoreStore and is called pre-query; evidence: entity_store.py requeue method + retrieval_orchestration.py call site + `test_retrieve_requeues_dimension_mismatched_card_and_counts_it`.
- `[VERIFIED]` AC-6 required span attrs all emitted with correct values, per-type sum == fill_selected (tested); evidence: `_finish` + `test_span_per_type_counts_sum_to_fill_selected`.
- `[SILENT][MEDIUM]` R1 — query_failed span omits `error_type`/`error_code` the lore sibling records (retrieval_orchestration.py ~249). Non-blocking; sibling-parity enhancement for 75-7.
- `[SEC][MEDIUM, pre-existing]` R2 — floor NPC names/appearance reach the prompt unsanitized via the existing `npc_roster` path (prompt_framework/core.py); not introduced by this diff (floor predates 75-5, unchanged). Out of AC-3 scope. Follow-up filed.
- `[SEC][MEDIUM, underlying]` R3 — `sanitize_player_text` doesn't strip chatml `<|im_start|>` tokens (protocol/sanitize.py:20). ADR-047 sanitizer gap, not 75-5 code; 75-5 correctly calls it. Lower risk on the default Anthropic backend. Follow-up filed.
- `[TEST][MEDIUM]` R4/R5/R6 — wiring test could assert `outcome=="success"` (currently pinned indirectly via the "Wiring Landmark"-in-prompt assertion); no test for the blank-action-text branch; span-names test could assert values (mitigated by the sibling values test). All hardening; non-blocking.
- `[EDGE][LOW]` R7 — `rejected_below_similarity` excludes top_k-truncated and floor-deduped candidates; span accounting could add `fill_skipped_over_budget` / dedup counters. Diagnostic granularity for 75-7.

**Blocking issues (Critical/High introduced by this diff):** None. The two security HIGHs are pre-existing/underlying-sanitizer (real, tracked, out of 75-5's AC-3 scope); the never-raises HIGHs are mitigated at the daemon boundary. All confirmed 75-5 findings are Medium/Low.

**Data flow traced:** player action → `_retrieve_entities_for_turn` → `retrieve_turn_context` (floor+fill, sanitized fill) → `RetrievedEntities` → `_build_turn_context` render → `TurnContext.retrieved_entity_*` → orchestrator Valley registration → narrator prompt. Safe: fill sanitized at the choke-point; failures recorded, never raised.

**Handoff:** To Neo (Architect) for spec-reconcile, then Morpheus (SM) for finish.

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-01T15:46:12Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-01 | — | — |

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Question** (non-blocking): the scene-present floor's full `Npc` profiles may ALREADY be injected by the live 75-2 `build_npc_working_set` → roster-section path. 75-5 must NOT double-inject the floor. The `floor: NpcWorkingSet` in `RetrievedEntities` exists for budget accounting + dedup; only the FILL sections (`retrieved_*`) should be registered into the Valley by 75-5's wiring. Affects `sidequest/server/session_helpers.py` / `orchestrator.py` (the Valley registration step) — Dev/Reviewer must confirm scene-present NPCs are not registered twice. *Found by TEA during test design.*
- **Gap** (non-blocking): `_SessionData` has no `entity_store` field, and nothing POPULATES the index yet — the card sync/reproject hook is 75-6. 75-5 must add `entity_store: EntityStore = field(default_factory=EntityStore)` to `_SessionData` (the wiring test seeds it manually); ongoing population/reproject is explicitly 75-6's scope, not a 75-5 gap. Affects `sidequest/server/session_state.py`. *Found by TEA during test design.*
- **Improvement** (non-blocking): AC-4 forces `EntityStore.requeue_dimension_mismatched` (75-4 omitted it). The sibling `LoreStore.mark_embedding_failed` is NOT exercised by 75-5 tests — the transient-retry path belongs to the live entity embedding-worker drain (75-6). Dev should mirror `requeue_dimension_mismatched` now and defer `mark_embedding_failed` to 75-6 when the worker drains entity cards. Affects `sidequest/game/entity_store.py`. *Found by TEA during test design.*
- **Improvement** (non-blocking): the daemon embedding seam (`DaemonClient.embed`) reaches the entity fill the same way it reaches lore. Reuse `retrieve_lore_context`'s exact failure taxonomy (daemon-unavailable / `DaemonRequestError` / oversized-query `ValueError`) — all three collapse to `outcome="query_failed"` for entities. Affects `sidequest/game/retrieval_orchestration.py`. *Found by TEA during test design.*

### Dev (implementation)

- **Gap** (non-blocking, by design): nothing POPULATES `sd.entity_store` with cards yet — the projection/sync hook is 75-6. Until 75-6 lands, `retrieve_turn_context` returns `no_candidates` in live play (the index is empty), so the new Valley sections never render at runtime even though the wiring is complete and proven (the wiring test seeds the store manually). This is the expected 75-5→75-6 boundary, not a defect. Affects `sidequest/server/session_state.py` (the empty default-factory store). *Found by Dev during implementation.*
- **Improvement** (non-blocking): the floor is computed twice per live turn (once in `retrieve_turn_context`, once in `_build_turn_context`), emitting `SPAN_NPC_WORKING_SET` twice. 75-7 can thread the already-built `NpcWorkingSet` through to dedupe the call. See the matching Dev deviation. Affects `sidequest/server/session_helpers.py` + `sidequest/game/retrieval_orchestration.py`. *Found by Dev during implementation.*
### Reviewer (code review)

- **Improvement** (non-blocking, security — pre-existing): floor NPC names/appearance reach the narrator prompt unsanitized via the existing `npc_roster` path. Affects `sidequest/agents/prompt_framework/core.py` (`_register_budgeted_npc_roster` / `_full_npc_line` — apply `sanitize_player_text` to outbound NPC name/appearance/last_seen_location, store untouched). Not introduced by 75-5; the fill surface this story adds IS sanitized. Recommend a dedicated sanitization story. *Found by Reviewer during code review.*
- **Improvement** (non-blocking, security — underlying): `sanitize_player_text` does not strip chatml/Llama tokenizer tokens (`<|im_start|>`, `<|im_end|>`, `<|user|>`, `<|assistant|>`, `<|system|>`) that AC-3 names as example vectors. Affects `sidequest/protocol/sanitize.py` (add a `<\|...\|>` pattern). ADR-047 gap, not 75-5 code; lower risk on the default Anthropic backend, exploitable on the Ollama opt-in. *Found by Reviewer during code review.*
- **Improvement** (non-blocking, observability): the `query_failed` span omits `retrieval.error_type` / `retrieval.error_code` that the lore sibling records — operators can't distinguish daemon-down vs model-fail vs malformed-reply. Affects `sidequest/game/retrieval_orchestration.py` (set both before `_finish` in the except clause, mirroring `lore_embedding.py`). Sibling-parity enhancement for 75-7. *Found by Reviewer during code review.*
- **Improvement** (non-blocking, observability): span accounting — `rejected_below_similarity` excludes top_k-truncated and floor-deduped candidates; consider `fill_skipped_over_budget` and a dedup counter so the GM panel distinguishes the rejection reasons. Affects `sidequest/game/retrieval_orchestration.py`. For 75-7. *Found by Reviewer during code review.*
- **Improvement** (non-blocking, test hardening): wiring test could assert `outcome=="success"` explicitly (currently pinned indirectly by the "Wiring Landmark"-in-prompt assertion); add coverage for the blank-action-text `query_failed` branch and `DaemonRequestError` (not just `DaemonUnavailableError`). Affects `tests/game/test_retrieval_orchestration.py`. *Found by Reviewer during code review.*
- **Question** (non-blocking, 75-6 contract): the fill dedup (`_floor_card_ids`) matches the `npc:<_slug(name)>` id convention; 75-6's store-population/reproject hook MUST create NPC cards via the projectors (`project_npc_card`) so the id convention holds, or the floor↔fill dedup silently misses. Affects `sidequest/game/entity_store.py` consumers (75-6). *Found by Reviewer during code review.*

### Dev — opening-turn span (carried from Dev findings)

- **Question** (non-blocking): `retrieve_turn_context` runs on EVERY turn including the chargen opening turn (wired at both `_run_opening_turn_narration` and the player-action handler) for AC-6's "every narrator turn emits the span." At the opening turn the store is empty → `no_candidates` span. Reviewer should confirm emitting the span on the (currently always-empty) opening turn is desired and not noise. Affects `sidequest/server/websocket_session_handler.py`. *Found by Dev during implementation.*

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Reviewer (audit)

- **TEA: `retrieve_turn_context` signature refinement** → ✓ ACCEPTED: the floor needs a `GameSnapshot`+`current_turn` and `TurnContext` is built downstream; refining the sketched signature is correct, and it mirrors the live `retrieve_lore_context`.
- **TEA: fill-only `retrieved_*` + separate `floor` field; per-type span counts are fill-only summing to `fill_selected_count`** → ✓ ACCEPTED: keeps the dedup contract and per-type sum invariant testable; verified by the GREEN span test.
- **Dev: `_sanitize_card` / `_floor_card_ids` helper shapes vs the sketched helpers** → ✓ ACCEPTED: same behavior, simpler; per-card sanitization at selection is the correct choke-point.
- **Dev: double `build_npc_working_set` call per live turn** → ✓ ACCEPTED: required by the unit contract; deterministic and cheap; 75-7 optimization noted.
- **Architect (spec-check): MP crash-release path emits no `retrieval.universal` span (Defer)** → ✓ ACCEPTED: consistent with the path's existing lore-skip (`lore_context=None`); deferring is correct.
- **UNDOCUMENTED — floor NPC text reaches the prompt unsanitized:** Spec (ADR-047 / CLAUDE.md) says player-influenced text must be sanitized before narrator prompts; the **fill** is sanitized (AC-3) but the **floor** (`npc_roster` via `prompt_framework/core.py`) renders player-influenced NPC names/appearance unsanitized. NOT introduced by this diff (the floor path predates 75-5 and is unchanged; 75-5 does not re-inject the floor) and out of AC-3's "retrieved EntityCard.content" scope. Severity: M (pre-existing). Flagged as a Delivery Finding for a dedicated sanitization follow-up — not a 75-5 blocker.

### Dev (implementation)

- **Helper shapes differ from the sketched `_apply_prompt_injection_sanitization` / `_dedupe_floor_and_fill`**
  - Spec source: session `## Technical Approach` → File Structure
  - Spec text: "Helper: `_apply_prompt_injection_sanitization(entity_cards)` … Helper: `_dedupe_floor_and_fill(floor_npcs, fill_npcs)`"
  - Implementation: used `_sanitize_card(card)` (per-card `model_copy` at fill-selection time, returning a sanitized copy that never mutates the stored card) and `_floor_card_ids(working_set)` + an inline `card.id not in floor_ids` set-membership filter for dedup (id-based, not list-diff).
  - Rationale: per-card sanitization at the selection point is the natural choke-point and satisfies `test_sanitization_does_not_mutate_the_stored_card`; id-based dedup is O(1) and matches the `npc:<slug>` id convention. Same behavior as the sketch, simpler shape.
  - Severity: minor
  - Forward impact: none — internal helpers, not a public contract.

- **`retrieve_turn_context` calls `build_npc_working_set` even though `_build_turn_context` also calls it → the floor is computed (and `SPAN_NPC_WORKING_SET` emitted) twice per live turn**
  - Spec source: session AC-1 + context-story-75-5.md line 27
  - Spec text: "Calls 75-2's `build_npc_working_set` to assemble the floor"
  - Implementation: the orchestration owns the floor call (unit tests pass a snapshot and expect the floor in the result), so the live path builds the working set inside `retrieve_turn_context` and again inside `_build_turn_context` for the existing roster injection.
  - Rationale: keeping the floor call inside `retrieve_turn_context` is required by the unit contract; the redundant production call is deterministic and cheap.
  - Severity: minor
  - Forward impact: 75-7 could thread the already-built working set in to drop the double call + duplicate span.

### TEA (test design)

- **`retrieve_turn_context` signature refined from the sketched `(turn_context, action_text, budget_tokens)`**
  - Spec source: session file `## Technical Approach` → File Structure
  - Spec text: "`retrieve_turn_context(turn_context, action_text, budget_tokens)` — main function"
  - Implementation (test-pinned contract): `async def retrieve_turn_context(entity_store: EntityStore, snapshot: GameSnapshot, action_text: str, *, current_turn: int, budget_tokens: int = DEFAULT_ENTITY_BUDGET_TOKENS, player_referenced_npcs: set[str] | None = None, client: DaemonClient | None = None, min_similarity: float = DEFAULT_RETRIEVAL_MIN_SIMILARITY) -> RetrievedEntities`
  - Rationale: the floor is assembled via `build_npc_working_set(snapshot, current_turn=…)` (needs a `GameSnapshot` + `current_turn`, not a `TurnContext`), and `TurnContext` is built *downstream* — `lore_context` is passed *into* `_build_turn_context` *after* retrieval, so `retrieve_turn_context` cannot receive a `TurnContext`. The fill needs the `EntityStore` + a `client` seam. This makes the signature a 1:1 sibling of the live `retrieve_lore_context(store, query_text, client, *, …)`. The sketched helpers `_apply_prompt_injection_sanitization` / `_dedupe_floor_and_fill` remain valid internal helpers (not pinned by tests).
  - Severity: minor
  - Forward impact: Dev implements to this signature; 75-7 reads the result's metric fields for the span.

- **Result is a `RetrievedEntities` dataclass; `retrieved_*` carry the SEMANTIC FILL only, with the floor in a separate `floor: NpcWorkingSet` field**
  - Spec source: session AC-1 / context-story-75-5.md line 32
  - Spec text: "Returns typed sections: `retrieved_npcs`, `retrieved_locations`, `retrieved_factions` (or None if empty)"
  - Implementation: the three `retrieved_*` fields hold the fill only (`None` when that type retrieved nothing — zero-byte-leak at the data level); the full-detail floor rides in `floor: NpcWorkingSet`. AC-2's "both tiers appear in the result" = `floor` populated AND `retrieved_*` populated.
  - Rationale: floor = full `Npc` profiles (75-2), fill = compact `EntityCard`s — different representations that cannot share one list without losing the detail tier. Separating them makes the dedup contract (floor NPC excluded from fill) and per-type fill counts directly testable.
  - Severity: minor
  - Forward impact: 75-7 dashboard consumes the per-type fill counts; the wiring registers a Valley section only for non-`None` fields.

- **Span per-type counts (`retrieval.npc_count` / `.location_count` / `.faction_count`) are FILL-only and sum to `retrieval.fill_selected_count`**
  - Spec source: context-story-75-5.md line 99
  - Spec text: "Per-type counts in the span sum correctly (npc + location + faction = total selected)"
  - Implementation: per-type counts exclude the floor and sum to `fill_selected_count`; `floor_count` / `floor_token_cost` track the floor separately.
  - Rationale: "total selected" = fill selected; folding the always-present floor into per-type counts would break the sum invariant and the dashboard's budget bar.
  - Severity: minor
  - Forward impact: 75-7 keys the per-type breakdown on this invariant.
### Architect (reconcile)

**Existing-entry verification:** all in-flight deviations are accurate and self-contained — spec sources exist and are quoted correctly:
- TEA (×3: signature refinement, fill-only result + separate `floor`, fill-only per-type span sum) — verified against context-story-75-5.md (line 27 "both the floor and the fill enter the prompt", line 99 "npc + location + faction = total selected") and session AC-1. ✓ Accurate.
- Dev (×2: helper shapes, double `build_npc_working_set` call) — verified against the session Technical Approach sketch. ✓ Accurate.
- Reviewer (audit): five ACCEPTED stamps + one UNDOCUMENTED floor-sanitization flag — verified. ✓ Accurate.
- AC deferral check: **no ACs were deferred** — all six are DONE (GREEN suite + spec-check confirmed). No accountability-table reconciliation needed (no-op).

**Missed deviations promoted to the canonical manifest:**

- **Narrator-context sanitization is applied to the fill (AC-3) but NOT to the floor — leaving a player-influenced injection surface unsanitized**
  - Spec source: session file AC-3; ADR-047; CLAUDE.md "Prompt Injection Sanitization Layer"
  - Spec text: AC-3 — "all retrieved `EntityCard.content` is sanitized via `sanitize_player_text` (ADR-047) before Valley injection … 75-5 applies sanitization at the retrieval → Valley injection step (the single choke-point)."
  - Implementation: 75-5 sanitizes the **fill** (`EntityCard.content`) at the `retrieve_turn_context` choke-point (`_sanitize_card`), satisfying AC-3 literally. The **floor** — scene-present NPC names/appearance rendered into the `npc_roster` prompt section via the pre-existing `prompt_framework/core.py` path — reaches the narrator prompt unsanitized. NPC identity fields are player-influenceable via the Yes-And path. This floor path predates 75-5 and is unchanged by this diff (75-5 explicitly does not re-inject the floor — no double-injection), so the gap is **not introduced or widened** by this story; AC-3's scope is "retrieved EntityCard.content" (the fill), which is compliant.
  - Rationale: surfaced by the security review while modelling 75-5's threat surface. Recorded here so the audit is complete: the floor is a real, separate, pre-existing injection surface outside AC-3's scope, tracked for a dedicated sanitization follow-up.
  - Severity: minor (pre-existing; default Anthropic narrator does not parse the highest-risk chatml vectors; Ollama opt-in backend is the exposure)
  - Forward impact: a follow-up story should sanitize outbound NPC name/appearance/last_seen_location in `_register_budgeted_npc_roster`/`_full_npc_line` (store untouched, mirroring `_sanitize_card`), and extend `sanitize_player_text` to strip chatml `<|im_start|>`-family tokens (ADR-047). Neither blocks 75-5.

No other missed deviations. The MP crash-release span gap (Architect spec-check) and the observability/test-hardening items (Reviewer) are captured as accepted deviations / Delivery Findings and are correctly out of 75-5's blocking scope.