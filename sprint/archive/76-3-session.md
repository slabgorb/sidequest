---
story_id: "76-3"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 76-3: expected_dim parity for the entity embed worker — mirror lore's dimension guard in embed_pending_entity_cards + EntityStore.update_embedding so a mid-session daemon model-dim change cannot write a stale-dim vector (currently self-heals one turn later via requeue).

## Story Details
- **ID:** 76-3
- **Jira Key:** (none — project uses no Jira)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-04T10:33:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T23:41:00Z | 2026-06-04T10:12:08Z | -48532s |
| red | 2026-06-04T10:12:08Z | 2026-06-04T10:23:39Z | 11m 31s |
| green | 2026-06-04T10:23:39Z | 2026-06-04T10:26:11Z | 2m 32s |
| review | 2026-06-04T10:26:11Z | 2026-06-04T10:33:00Z | 6m 49s |
| finish | 2026-06-04T10:33:00Z | - | - |

## Technical Approach

**Reference implementation:** The lore embedding worker (`sidequest/game/lore_embedding.py`) already implements the dimension-guard pattern to prevent stale-dimension vector writes during the retrieve/worker race.

The pattern works as follows:
1. Capture the embedding dimension from the first successful daemon response (lore_embedding.py lines 235-236)
2. Pass `expected_dim` to `LoreStore.update_embedding(frag_id, embedding, expected_dim=expected_dim)` (line 237)
3. `update_embedding` returns `False` if the vector's dimension doesn't match `expected_dim`, preventing the write and keeping the fragment pending for re-embedding (lines 238-261 lore_embedding.py)

**The problem:**
- `EntityStore.update_embedding()` (entity_store.py line 179) does not accept an `expected_dim` parameter
- `embed_pending_entity_cards()` (entity_embedding.py line 132) calls `store.update_embedding(card_id, response["embedding"])` with no dimension guard
- When the daemon changes embedding models mid-session (e.g., MiniLM-384 → MiniLM-768), stale-dimension vectors write back and clear the pending flag, making cards unretrievable forever
- The requeue mechanism in `EntityStore.requeue_dimension_mismatched()` catches this *after the fact* on the next retrieval, self-healing one turn later — not preventing the corrupt write

**The fix:**
1. Add `expected_dim: int | None = None` parameter to `EntityStore.update_embedding()`
2. Return `bool` instead of `None` (matching `LoreStore.update_embedding`)
3. Refuse the write if `expected_dim` is set and the vector length doesn't match; return `False` to keep the card pending
4. Capture `expected_dim` on the first successful daemon response in `embed_pending_entity_cards()` (before the loop)
5. Pass `expected_dim` to all `update_embedding()` calls in the entity worker (matching lore_embedding.py pattern lines 235-261)
6. Emit OTEL span events for dimension mismatches (matching lore telemetry)

**Anti-orphan contract:** Like `LoreStore`, `EntityStore.update_embedding()` must never silently clear the pending flag while writing a mismatched-dimension vector. The dimension guard prevents the corrupt write; requeue on the *next* turn detects and re-embeds any cards from prior mid-session model changes.

## Acceptance Criteria

1. **Unit test:** `EntityStore.update_embedding()` rejects writes when `expected_dim` is set and vector length doesn't match; the write returns `False` and the card stays pending
2. **Unit test:** `embed_pending_entity_cards()` captures `expected_dim` on the first successful response and passes it to all subsequent `update_embedding()` calls
3. **Dimension-mismatch OTEL event:** The entity worker emits `embed_failed` span events with `reason="dim_mismatch_writeback_refused"` (matching lore telemetry), including `written_dim` and `expected_dim` attributes
4. **Wiring/integration test:** The dimension guard fires in a production call path — construct a scenario where a daemon model change is detected mid-embed, verify the stale vector write is refused and the card remains pending for re-embedding (do not use source-text regexes; use behavior assertions on the store state)
5. **Regression guard:** Stale-dimension vectors do not reach `query_by_similarity()` (the card stays pending, not silently orphaned)

## Sm Assessment

Story 76-3 is a clean, well-scoped 2pt parity fix with a concrete reference implementation already in the tree (`lore_embedding.py` dimension guard). No discovery ambiguity — the gap is explicit (`EntityStore.update_embedding` lacks `expected_dim`; `embed_pending_entity_cards` calls it ungated), and the fix is "mirror the lore pattern." Single repo (sidequest-server), no cross-repo coordination, no ADR note required (this is implementation parity within an accepted pattern, not a new decision).

TDD is the right workflow despite the small point count: the value of the story is *behavior* (a stale-dim write is refused, not self-healed a turn later), which is exactly what a RED test should pin before any code moves. TEA should write the failing test against store/worker behavior — assert the card stays pending and no mismatched vector reaches `query_by_similarity()` — not against source text. The CLAUDE.md wiring-test mandate is captured in AC#4; hold the line on it. OTEL emission (AC#3) is non-negotiable per the observability principle — the `embed_failed`/`dim_mismatch_writeback_refused` span is the lie detector proving the guard fired.

Watch items for downstream agents: (1) `update_embedding` changes return type `None`→`bool` — sweep all callers, not just the worker, or the contract change silently breaks an unaudited consumer; (2) keep the existing `requeue_dimension_mismatched` self-heal intact — this fix is *additive* prevention, not a replacement for the next-turn recovery of cards written before a mid-session model change. Routing to The Architect (tea) for RED.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (failing — ready for Dev)

**Test File:**
- `tests/game/test_entity_embedding.py` (new) — mirrors `tests/game/test_lore_embedding.py` worker tests over `entity_store` + `entity_embedding`.

**Tests Written:** 9 tests covering all 5 ACs.
- 8 fail (feature absent) — verified RED for the right reason (`TypeError: EntityStore.update_embedding() got an unexpected keyword argument 'expected_dim'` on the unit tests; `assert 2 == 1` on the worker/wiring tests because both cards are written ungated today).
- 1 passes (`test_worker_embeds_all_when_dims_consistent`) — a deliberate happy-path test proving the guard is inert when the model is stable; it is non-vacuous (asserts `embedded == 2`, `failed_embed_error == 0`, empty pending) and is expected to stay green.

**AC → test map:**
| AC | Test(s) | RED? |
|----|---------|------|
| AC1 update_embedding expected_dim/bool | `test_matching_dim_writes_and_returns_true`, `test_mismatched_dim_refuses_write_and_returns_false`, `test_mismatch_refusal_does_not_orphan_an_already_embedded_card`, `test_no_expected_dim_preserves_legacy_unconditional_write`, `test_empty_vector_still_rejected_loudly` | failing |
| AC2 worker captures + passes expected_dim | `test_worker_refuses_dim_mismatched_writeback` (+ happy-path `test_worker_embeds_all_when_dims_consistent`, green) | failing |
| AC3 dim-mismatch OTEL event | `test_worker_emits_dim_mismatch_span_event` | failing |
| AC4 wiring (production worker path) | `test_mid_session_model_change_does_not_orphan_card_via_real_worker` | failing |
| AC5 no stale vector reaches query_by_similarity | covered by AC1 `..._does_not_orphan_...` + AC4 wiring test (`npc:skarl` absent from `query_by_similarity`) | failing |

### Rule Coverage (python.md lang-review)

| Rule | Coverage | Status |
|------|----------|--------|
| #3 type annotations at boundaries | `expected_dim: int \| None` param + `bool` return asserted behaviorally (`written is True/False`) | enforced via tests |
| #4 logging / error-path signalling | OTEL `embed_failed` span event asserted (`test_worker_emits_dim_mismatch_span_event`) — the GM-panel proof the error path fired | failing |
| #6 test quality (no vacuous asserts) | self-checked: every test asserts concrete state/values; the one green test asserts counts+pending, not truthiness | clean |
| #9 async/await | worker tests use `@pytest.mark.asyncio` and `await` the real coroutine | enforced |

**Rules checked:** 4 of 13 applicable to this change have test coverage (the rest — deserialization, paths, resource leaks, deps, input-validation — are N/A to an in-memory store + worker counter change).
**Self-check:** 0 vacuous tests found.

**Wiring test:** `test_mid_session_model_change_does_not_orphan_card_via_real_worker` drives the real `embed_pending_entity_cards` (the *only* production caller of `EntityStore.update_embedding`) — behavior-driven, no source-text grep (server CLAUDE.md *No Source-Text Wiring Tests*).

**Handoff:** To Dev (Agent Smith) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/game/entity_store.py` — `update_embedding` gains `*, expected_dim: int | None = None` and returns `bool`. Empty-vector `ValueError` still fires first; when `expected_dim` is set and the vector length differs, the write is refused (`return False`) leaving the card untouched + pending; `None` → unconditional write (back-compat). Mirrors `LoreStore.update_embedding`.
- `sidequest/game/entity_embedding.py` — worker pins `expected_dim` on the first successful embed and threads it to every write-back. On refusal: `result.failed_embed_error += 1`, emits the `embed_failed` span event with `reason="dim_mismatch_writeback_refused"` + `written_dim`/`expected_dim`/`card_id`, logs a warning, and continues (card stays pending). Mirrors `lore_embedding.embed_pending_fragments` lines 234–261.

**Tests:** 9/9 passing for the story (GREEN). Regression: 26 existing entity tests + 58 dispatch/retrieval/lore-embed tests unaffected. `ruff` clean, `pyright` 0 errors on both changed files.
**Branch:** `feat/76-3-entity-embed-dim-guard` (pushed to origin).

**Minimalism note:** Implemented exactly the explicit-`expected_dim` guard the tests pin — did NOT port lore's `_current_embedding_dim()` derivation fallback (TEA scoped it out; no entity caller omits `expected_dim`). The existing `requeue_dimension_mismatched` self-heal is left fully intact — this change is additive prevention, not a replacement.

**Handoff:** To The Architect (verify phase).

## Subagent Results

Only `preflight` and `security` are enabled via `workflow.reviewer_subagents`; the other 7 are disabled — their domains were self-assessed by the Reviewer (tagged in the assessment below).

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 79 pass / 0 fail, lint+pyright clean, 0 smells | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings — self-assessed [EDGE] |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings — self-assessed [SILENT] |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings — self-assessed [TEST] |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings — self-assessed [DOC] |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings — self-assessed [TYPE] |
| 7 | reviewer-security | Yes | findings | 1 (medium: OTEL aggregate-attr parity gap) | confirmed 1 (non-blocking), dismissed 0, deferred 0 |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings — self-assessed [SIMPLE] |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings — self-assessed [RULE] |

**All received:** Yes (2 enabled returned; 7 disabled via settings, self-assessed)
**Total findings:** 1 confirmed (medium, non-blocking), 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** daemon embed response → `embedding = response["embedding"]` → first-success pins `expected_dim = len(embedding)` → `EntityStore.update_embedding(card_id, embedding, expected_dim=…)`. On length match: vector written, `embedding_pending=False`, `retry_count=0`, returns `True`, `result.embedded += 1`. On mismatch: returns `False`, card untouched (embedding stays `None`, `pending` stays `True`), `failed_embed_error += 1`, `embed_failed` span event emitted, warning logged, `continue`. The refused vector never reaches `query_by_similarity` (it is never written). Safe.

**Findings (severity-tagged, dispatch-tagged):**

- `[SEC]`/`[RULE]` **[MEDIUM — non-blocking]** Entity worker's final span emits `entity.embedded` + `entity.failed` (the sum) but not the `entity.failed_embed_error` / `entity.failed_text_too_large` sub-counters that the lore worker emits (`lore_embedding.py:266-267`); the module docstring promises "the GM panel reads one shape." **Confirmed but does not block:** verified this is a **pre-existing** gap (those two `span.set_attribute` lines are unchanged context, and `failed_embed_error` was already incremented at `entity_embedding.py:95` before 76-3) — NOT introduced by this diff and not in any AC. The mandatory OTEL rule ("every subsystem *decision* emits a span") is **satisfied**: the dim-mismatch decision emits a distinct `embed_failed` event carrying `reason`/`written_dim`/`expected_dim`/`card_id` (AC-3, tested). 76-3 makes the sub-counter aggregate marginally more useful (dim-mismatch now also feeds `failed_embed_error`), so I record the two-line parity addition as a fast-follow Improvement rather than blocking GREEN, all-ACs-met work for a pre-existing aggregate-attribute gap.

**Self-assessed domains (disabled subagents):**

- `[EDGE]` Boundary paths enumerated: (a) first card mismatched → `expected_dim` is `None` on iter 1, so it is pinned from that card and the write always succeeds — correct, the first successful embed *defines* the session dim (matches lore). (b) empty vector → `not embedding` raises `ValueError` *before* the dim check (`expected_dim=0` cannot be reached as a guard value). (c) `max_per_run=0` → empty slice, loop body never runs — unaffected. (d) all-consistent dims → guard inert, `embedded == N` (covered by `test_worker_embeds_all_when_dims_consistent`). No unhandled boundary.
- `[SILENT]` No swallowed errors introduced. The dim-mismatch branch is loud: counter + span event + `logger.warning`. `mark_embedding_failed` is intentionally *not* called on this path so a model-swap (not the card's fault) does not burn the card's retry budget — VERIFIED correct, matches lore. KeyError on unknown id still propagates (No Silent Fallbacks preserved).
- `[TEST]` 9 tests, all assertions meaningful (concrete state/values, not truthiness). Wiring test (`test_mid_session_model_change_does_not_orphan_card_via_real_worker`) drives the real worker and asserts the refused card is absent from `query_by_similarity` — behavior-driven, no source grep (complies with *No Source-Text Wiring Tests*). The single green happy-path test is non-vacuous (`embedded==2`, `failed_embed_error==0`, empty pending). No skips, no coupling to private internals.
- `[DOC]` Docstrings updated accurately on both `update_embedding` (documents `expected_dim`, the `bool` return, the refusal semantics, and the orphan it prevents) and the worker (inline comments explain the pin + refusal). No stale/misleading comments.
- `[TYPE]` `update_embedding(..., *, expected_dim: int | None = None) -> bool` — keyword-only, fully annotated, return type narrowed from `None` to `bool` (matches `LoreStore`). `expected_dim: int | None = None` local in the worker is annotated. No stringly-typed APIs, no unsafe casts. pyright clean.
- `[SIMPLE]` Minimal implementation — two `span.set_attribute`-free additions: one guard line in the store, the pin+refusal block in the worker. No dead code, no over-engineering. Correctly did NOT port lore's `_current_embedding_dim()` derivation fallback (no entity consumer needs it) — restraint, not omission.
- `[RULE]` python.md rules enumerated against the diff: #2 mutable defaults — `expected_dim=None` (clean); #3 type annotations at boundaries — public `update_embedding` fully annotated (clean); #4 logging — `logger.warning` with lazy `%`-style args, no PII, recoverable-anomaly level (clean); #6 test quality — no vacuous asserts (clean); #9 async — no blocking calls / missing awaits added (clean). No violations.

### Rule Compliance

| Rule (source) | Instances in diff | Verdict |
|---------------|-------------------|---------|
| No Silent Fallbacks (CLAUDE.md) | dim-mismatch refusal, KeyError on unknown id, empty-vector ValueError | compliant — all loud |
| OTEL Observability Principle (CLAUDE.md) | dim-mismatch decision | compliant — `embed_failed` event fires (aggregate sub-counter parity noted as non-blocking improvement) |
| No Source-Text Wiring Tests (CLAUDE.md) | wiring test | compliant — drives real worker, behavior assertion |
| Verify Wiring, Not Just Existence (CLAUDE.md) | sole prod caller = worker:139, updated | compliant — end-to-end test through worker |
| python.md #2/#3/#4/#6/#9 | see [RULE] above | compliant |

### Devil's Advocate

Assume this code is broken. The most suspicious move is narrowing a public method's return type from `None` to `bool`: any caller that did `if store.update_embedding(...) is None:` or relied on the falsy `None` would now silently invert. I enumerated every call site — one production caller (`entity_embedding.py:139`, rewritten to consume the bool) and the rest tests that ignore the return on the back-compat `expected_dim=None` path (always `True`). So the contract change cannot strand an unaudited consumer. Next attack: a malicious/buggy daemon. It could return a million-float vector — `list(embedding)` copies it into memory unbounded. But the daemon is a local trusted Unix-socket sidecar, not attacker-reachable, and this length risk predates 76-3. It could return an empty list on a "successful" response — `update_embedding` would raise `ValueError` outside the worker's `try`, crashing the span; but `DaemonClient.embed()` already surfaces empty/missing/non-numeric responses as `DaemonRequestError` (caught at line 97), so the successful-but-empty path is unreachable, and again pre-existing. A confused operator reading the GM panel might think no dim-mismatch occurred because the aggregate `entity.failed` lumps it with text-too-large failures — that is exactly the parity finding, and it is mitigated by the per-decision `embed_failed` event which *is* on the span. Race angle: a retrieve-time `requeue_dimension_mismatched` could flip a card's pending flag mid-embed; the `expected_dim` guard is precisely the defense — a stale-dim write-back is refused, and the card is re-embedded next pass on the live dim. What about the *first* card being the stale one? It pins `expected_dim` to itself and succeeds; if it is genuinely stale, the existing per-turn requeue self-heal catches it on the next retrieval — the additive guard does not regress that backstop. Nothing here rises to High/Critical; the one real observation is the non-blocking OTEL aggregate parity.

**Pattern observed:** Faithful sibling-parity with `lore_embedding.embed_pending_fragments` (pin-on-first / refuse-on-mismatch / event-on-refusal) at `entity_embedding.py:76-160`.
**Error handling:** dim-mismatch is counted, evented, logged, and the card left pending — `entity_embedding.py:140-162`.

**Handoff:** To SM for finish-story.

## Delivery Findings

### TEA (test design)
- No upstream findings.

### Dev (implementation)
- No upstream findings.

### Reviewer (code review)
- **Improvement** (non-blocking): The entity embed worker's final `entity_embedding.worker` span omits the `entity.failed_embed_error` / `entity.failed_text_too_large` sub-counter attributes that the lore worker emits (`lore_embedding.py:266-267`), so the GM panel cannot break down entity-embed failures at the aggregate-span level without parsing individual `embed_failed` events. Affects `sidequest/game/entity_embedding.py` (add two `span.set_attribute(...)` lines after the existing `entity.failed` at ~line 165, mirroring lore). Pre-existing gap (from 75-6), made marginally more relevant by 76-3 routing dim-mismatch refusals into `failed_embed_error`. *Found by Reviewer during code review.*

## Impact Summary

**Upstream Effects:** No upstream effects noted
**Blocking:** None

### Deviation Justifications

2 deviations

- **Did not test the `_current_embedding_dim()` derivation fallback that `LoreStore.update_embedding` provides**
  - Rationale: Session scope (highest authority) explicitly conditions the guard on "expected_dim is set"; the sole entity caller (the worker) always threads `expected_dim`, so the derivation fallback lore added for predating callers has no consumer here. Adding it would be untested scope creep beyond the session spec.
  - Severity: minor
  - Forward impact: If a future non-worker caller of `EntityStore.update_embedding` omits `expected_dim`, it will not get cross-dim protection. Acceptable now (no such caller); revisit if one is added. The existing per-turn `requeue_dimension_mismatched` self-heal still backstops any stored mismatch.
- **Ran pytest directly instead of via the `testing-runner` subagent**
  - Rationale: Documented session-memory hazard — `testing-runner` hallucinates per-test output (including false GREEN) and overwrites `.session/{story}-session.md` with its results cache (untracked → unrecoverable). Direct run gives trustworthy counts and protects the session file.
  - Severity: minor
  - Forward impact: none — RED verified with real, quoted pytest output.

## Design Deviations

### TEA (test design)
- **Did not test the `_current_embedding_dim()` derivation fallback that `LoreStore.update_embedding` provides**
  - Spec source: session "Technical Approach" steps 1–3 + story title ("mirror lore's dimension guard")
  - Spec text: "Refuse the write if `expected_dim` **is set** and the vector length doesn't match; return `False`"
  - Implementation: Tests pin only the explicit-`expected_dim` guard. `test_no_expected_dim_preserves_legacy_unconditional_write` asserts that with no `expected_dim` the write is unconditional (NOT derived-from-store like lore). I did not require Dev to port lore's `_current_embedding_dim()` derivation fallback.
  - Rationale: Session scope (highest authority) explicitly conditions the guard on "expected_dim is set"; the sole entity caller (the worker) always threads `expected_dim`, so the derivation fallback lore added for predating callers has no consumer here. Adding it would be untested scope creep beyond the session spec.
  - Severity: minor
  - Forward impact: If a future non-worker caller of `EntityStore.update_embedding` omits `expected_dim`, it will not get cross-dim protection. Acceptable now (no such caller); revisit if one is added. The existing per-turn `requeue_dimension_mismatched` self-heal still backstops any stored mismatch.
- **Ran pytest directly instead of via the `testing-runner` subagent**
  - Spec source: TEA agent definition `<workflow>` step 6 / Agent Behavior Guide ("Tests: Use `testing-runner` subagent, never run directly")
  - Spec text: "Spawn `testing-runner` to verify RED state"
  - Implementation: Verified RED with `uv run pytest -n0` directly.
  - Rationale: Documented session-memory hazard — `testing-runner` hallucinates per-test output (including false GREEN) and overwrites `.session/{story}-session.md` with its results cache (untracked → unrecoverable). Direct run gives trustworthy counts and protects the session file.
  - Severity: minor
  - Forward impact: none — RED verified with real, quoted pytest output.

### Dev (implementation)
- No deviations from spec. Implemented the minimal explicit-`expected_dim` guard exactly as the session Technical Approach and TEA's tests specify; honored TEA's scoping-out of the lore `_current_embedding_dim()` derivation fallback rather than adding untested scope.

### Reviewer (audit)
- **TEA: did not test the `_current_embedding_dim()` derivation fallback** → ✓ ACCEPTED by Reviewer: session scope (highest authority) conditions the guard on "expected_dim is set," the sole entity caller always threads it, and the per-turn `requeue_dimension_mismatched` self-heal backstops any stored mismatch. Porting the fallback would be untested scope creep. Sound.
- **TEA: ran pytest directly instead of via `testing-runner`** → ✓ ACCEPTED by Reviewer: documented session-memory hazard (testing-runner hallucinates output / clobbers the session file); preflight independently re-ran the suite (79 green) with real output, so RED/GREEN are both evidence-backed. Sound.
- **Dev: no deviations** → ✓ ACCEPTED by Reviewer: confirmed the diff implements exactly the explicit-`expected_dim` guard the tests pin, with no added abstraction.
- No undocumented deviations found. The one Reviewer observation (OTEL aggregate sub-counter parity) is a pre-existing gap recorded as a non-blocking Delivery Finding, not a spec deviation of this story.