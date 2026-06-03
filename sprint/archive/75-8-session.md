---
story_id: "75-8"
jira_key: ""
epic: "75"
workflow: "tdd"
---
# Story 75-8: Universal retrieval: end-to-end integration wiring test

## Story Details
- **ID:** 75-8
- **Jira Key:** (none — SideQuest is Jira-less)
- **Workflow:** tdd
- **Stack Parent:** 75-7 (dependency, merged)

## Story Context

This is the capstone wiring test for Epic 75 (ADR-118: Universal Retrieval Layer). Stories 75-1 through 75-7 are all merged:
- **75-1** — Restored runtime lore accretion into the RAG (per-turn fact embedding)
- **75-2** — Ported budgeted NPC working-set selection (scene-present full, others abbreviated)
- **75-3** — ADR-118 design document (universal retrieval vision)
- **75-4** — EntityCard model + per-type projectors
- **75-5** — `retrieve_turn_context()` floor+fill orchestration + per-turn token budget
- **75-6** — Card sync/reproject hook wired to 75-1's accretion trigger
- **75-7** — OTEL `retrieval.universal` instrumentation + GM-panel surface

The universal retrieval layer allows player actions to flow through the full pipeline: action → `retrieve_turn_context` floor+fill selection → EntityCard projections → Valley-zone injection into the narrator prompt. The system must verify that NPCs, locations, and factions are actually retrieved (by semantic relevance and floor guarantee) and injected into the prompt, not snapshot-dumped as inert blobs.

**Per ADR-118 § D4** the retrieval contract is:
- **FLOOR** — scene-present entities from 75-2 working-set selection (always included, full detail, counted against budget first)
- **FILL** — semantic top-k over non-floor cards (embed action text once, fill remaining budget until exhausted)
- **INJECT** — AttentionZone.Valley as typed sections (retrieved_npcs, retrieved_locations, retrieved_factions) with zero-byte-leak discipline

**Per project doctrine** ("Every Test Suite Needs a Wiring Test"), this test must verify the universal-retrieval seam is imported, called, and reachable from a real production code path — not a synthetic test fixture.

## Acceptance Criteria (Derived from ADR-118)

1. **Full pipeline wiring test:** player action triggers a turn flow that calls `retrieve_turn_context()` and injects EntityCards into AttentionZone.Valley (verify: no synthetic test harness, call traces from real production handlers).

2. **Floor guarantee:** scene-present NPCs from the working-set floor (75-2 selection) are always included in the retrieved set, full detail, even if semantic similarity is low.

3. **Semantic fill:** non-floor entities are retrieved by semantic relevance (embed the action text, top-k over candidate cards, apply similarity floor per DEFAULT_RETRIEVAL_MIN_SIMILARITY).

4. **Budget enforcement:** total retrieved tokens (floor + fill) remain under the per-turn budget; fill stops when budget is exhausted.

5. **Type-tagged injection:** retrieved cards are injected as typed sections in Valley (retrieved_npcs, retrieved_locations, retrieved_factions); no untagged blob carry. Silent no-op per zero-byte-leak doctrine (None → no section registered).

6. **OTEL observability:** the `retrieval.universal` span fires with floor count, fill counts/tokens, per-type counts, similarity floor rejections, and outcome (success vs. failure modes: query embed failed, budget exhausted, no candidates, dimension mismatch). The GM panel can verify retrieval engaged vs. narrator improvised.

7. **Card projections reachable:** EntityCard `to_card()` projectors for NPC, location, and faction are called in the retrieval path; the content field is embeddable and not a data dump.

8. **Integration test passes:** a real scenario turn with player action → asserts retrieved set contains expected NPCs/locations/factions → snapshot never carries a full npc_pool blob into the prompt (supersedes ADR-059 full-blob injection for the retrieved-NPC channel).

## Sm Assessment

**Decision: PROCEED to RED (TEA).** Story 75-8 is the capstone end-to-end wiring test for Epic 75 (ADR-118 Universal Retrieval Layer). All predecessors (75-1..75-7) are merged; dependency 75-7 landed via PR #342. Branch `feat/75-8-universal-retrieval-e2e-wiring-test` is cut from current `sidequest-server/develop` (#594, baff0ae4). This is a **test-only** story (2 pts) — no new feature behavior ships.

**Spec gap handled:** the YAML carried zero acceptance criteria — the title was the whole spec. ACs were derived from ADR-118 (§D4 floor+fill, §D5 OTEL, the implementation-story list) and recorded both in this session (8 ACs) and in `sprint/context/context-story-75-8.md` (validated `[OK]`).

**Load-bearing guardrail for TEA/Dev (from Architect/Leonard, see `.session/75-8-tandem-architect.md`):** this MUST be a real wiring test, not a synthetic fixture. Enter via the production delegate `handler._retrieve_entities_for_turn` (websocket_session_handler.py:2986) — a direct `retrieve_turn_context()` call is the #1 no-op trap and proves nothing. Net-new value over 75-7 is the **Valley injection half** (session_helpers.py render_entity_section → orchestrator.py register_section, AttentionZone.Valley). Model after `tests/server/dispatch/test_universal_retrieval_dispatch.py`; keep it in `tests/server/dispatch/` (offline — fake `embed()`, pure-cosine `query_by_similarity`, `InMemorySpanExporter`, no PG/daemon/genre-pack env). Two corrections to watch: (1) there is **no `to_card()` method** — projectors are module functions `project_{npc,location,faction}_card`; (2) floor entities are **deduped out of the fill** (retrieval_orchestration.py:268), so fill candidates must be seeded as NOT-scene-present or the test silently no-ops. Source-text/regex wiring tests are banned by server CLAUDE.md.

**If the wiring test cannot reach the seam from production without editing production code, that is a real 75-5/75-6 integration gap** — log it as a blocking Delivery Finding and route back to SM, do not absorb a fix into this test-only story.

## TEA Assessment

### Red Phase (test writing)

**Tests Required:** Yes

**Test Files:**
- `sidequest-server/tests/server/dispatch/test_universal_retrieval_e2e.py` — capstone end-to-end wiring suite for the universal retrieval layer (ADR-118).

**Tests Written:** 6 tests covering all 8 derived ACs (the ACs collapse into one end-to-end arc; coverage map below).

**Status:** **GREEN-on-arrival** (see honesty note). All 6 pass; full `tests/server/dispatch/` dir = 172 passed, 17 skipped (no sibling collision). ruff format + ruff check clean.

**AC → Test coverage map:**
| AC | Test |
|----|------|
| 1 Full-pipeline reachability (no synthetic harness) | `test_production_delegate_reaches_orchestrator_and_fires_span` + every test enters via `handler._retrieve_entities_for_turn` |
| 2 Floor guarantee / floor-vs-fill dedup | `test_floor_npc_not_double_injected_into_fill` |
| 3 Semantic fill | `test_capstone_action_to_fill_to_valley_npc_section` (off-stage card fills) |
| 4 Budget enforcement | exercised on the real path (budget 4000, card fits); span `fill_selected_count` asserted in `test_capstone_span_attributes_reflect_successful_fill` |
| 5 Type-tagged injection + zero-byte-leak | `test_capstone_action_to_fill_to_valley_npc_section` (typed `retrieved_npcs` Valley section) + `test_zero_byte_leak_absent_types_register_no_valley_section` |
| 6 OTEL observability | `test_capstone_span_attributes_reflect_successful_fill` + `test_production_delegate_...fires_span` |
| 7 Projectors reachable / embeddable content | covered transitively: the fill content (`project_*_card` shape) reaches the Valley section, asserted by content substring |
| 8 Integration test passes (no full npc_pool blob; ADR-059 superseded for retrieved-NPC channel) | the whole suite — fill is the typed Valley section, not a verbatim pool dump |
| (mandatory) Wiring → GM panel | `test_event_reaches_watcher_hub_via_production_delegate` |

### Rule Coverage (lang-review/python.md)
| Rule | Coverage | Status |
|------|----------|--------|
| #6 Test quality (no vacuous asserts, correct mock targets, real assertions) | self-checked: 0 vacuous; every test asserts specific values (card id in fill, content in Valley section, floor NPC excluded, span outcome/np_count); monkeypatch targets the import site `sidequest.game.retrieval_orchestration.DaemonClient`/`.tracer` (where USED), not where defined | pass |
| #9 Async pitfalls (missing await) | all coroutine calls awaited; `@pytest.mark.asyncio` on every async test (matches 75-7 sibling) | pass |
| server CLAUDE.md "No Source-Text Wiring Tests" | no `read_text()`/regex on source — assertions are span/section/watcher-event behaviour | pass |

**Self-check:** 0 vacuous tests found.

**HONESTY NOTE — GREEN-on-arrival (RED-phase tension):** This is a *capstone verification* story: the implementation (75-4..75-7) is already merged, so a correctly-wired pipeline makes these tests pass immediately. There is **no failing-RED → Dev-GREEN cycle** here because there is no feature to implement — the deliverable IS the wiring proof. Non-vacuity is nonetheless demonstrated: the suite genuinely FAILED on first run (2 real failures — the fixture's `sd.orchestrator` is a `MagicMock`, so `build_narrator_prompt` returned an empty mock; fixed by driving a real `Orchestrator()` for the prompt-assembly half per the `test_seed_valley_injection.py` pattern). The assertions check concrete values, so a real 75-5/75-6 wiring regression WOULD turn them red.

**Handoff:** To Dev (Ponder Stibbons). **No implementation is expected** — Dev should confirm GREEN against develop and advance to review. If Dev disagrees that this is verification-only, that is a scope question for SM, not a license to add production code under a test-only story.

## Dev Assessment

**Implementation Complete:** Yes (no production code required — verification story)

**Files Changed:**
- None in production. The deliverable is the test suite TEA authored: `sidequest-server/tests/server/dispatch/test_universal_retrieval_e2e.py`.

**Tests:** 6/6 passing (GREEN), confirmed against current develop (server `4cc6812f`, off develop `baff0ae4`). `ruff check` clean, `ruff format --check` clean.

**Branch:** `feat/75-8-universal-retrieval-e2e-wiring-test` (pushed to origin).

**What Dev did:** Confirmed the GREEN-on-arrival state Igor (TEA) documented. The ADR-118 universal-retrieval pipeline (built and merged across 75-4..75-7) is correctly wired end-to-end — the capstone suite drives the real `handler._retrieve_entities_for_turn` delegate through floor+fill into the Valley-zone prompt injection and passes. Per *Minimalist Discipline* and the test-only story scope, **no production code was written** — there was no failing test demanding it, and writing any would be scope creep into a verification story. No deviations from the TEA-handoff scope.

**Self-review:**
- Code wired to real components: yes — the tests assert against the production delegate, real `Orchestrator.build_narrator_prompt`, real `watcher_hub` (not synthetic fixtures).
- Follows project patterns: yes — mirrors `tests/server/dispatch/test_universal_retrieval_dispatch.py` (75-7) and `tests/agents/test_seed_valley_injection.py`.
- All ACs met: yes — see TEA AC→test map.
- Error handling: N/A (test-only).

**Handoff:** To Reviewer (Granny Weatherwax) for code review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (one trivial spec-text inaccuracy, code is correct)
**Mismatches Found:** 1 (trivial)

Substance check of the 6-test suite against the 8 derived ACs (I authored the production-seam survey in `.session/75-8-tandem-architect.md`, so this is a direct read against known seams):

- **AC1 (reachability)** — Aligned. Every test enters via the real `handler._retrieve_entities_for_turn` delegate (the live seam at websocket_session_handler.py:2986). The #1 no-op trap (a direct `retrieve_turn_context()` call) is avoided. Correct.
- **AC2 (floor)** — Aligned. The suite pins the floor-vs-fill **dedup** invariant (`test_floor_npc_not_double_injected_into_fill`) — the half 75-8 owns. The "floor always included full-detail" half rides the npc-roster path (`npc_working_set`), which is 75-2's channel and out of the entity-fill scope. No gap.
- **AC3 (semantic fill)** — Aligned (`test_capstone_action_to_fill_to_valley_npc_section`, off-stage card fills under cosine).
- **AC4 (budget)** — Aligned (light). The success-path budget is exercised and `fill_selected_count` asserted; the deep `budget_exhausted` branch is covered by 75-5's own unit suite (`tests/game/test_retrieval_orchestration.py`), not re-pinned here. Appropriate scope for a capstone wiring test.
- **AC5 (typed injection + zero-byte-leak)** — Aligned, both directions: a present type registers exactly one typed Valley section; absent types register NO section (`test_zero_byte_leak_absent_types_register_no_valley_section`).
- **AC6 (OTEL)** — Aligned (`retrieval.universal` span outcome + per-type counts).
- **AC7 (projectors reachable)** — **Mismatch (Ambiguous spec — Cosmetic, Trivial).** The AC text says "EntityCard `to_card()` projectors" — **no `to_card()` method exists**; projection is module functions `project_{npc,location,faction}_card` (entity_card.py:173/196/212). The test correctly asserts projected content reaching the Valley section. **Spec:** "to_card() projectors are called." **Code:** module-level `project_*_card` functions on the sync path; the retrieval path consumes already-projected cards. **Recommendation: C (clarify spec)** — the AC wording is an artifact of ADR-118's prose; the code and test are correct. SM/TEA already corrected this in the session ACs and TEA's deviation log. I will formalize the wording reconciliation in the spec-reconcile phase. No code change.
- **AC8 (no full npc_pool blob)** — Aligned: the fill is a typed Valley section, not a verbatim pool dump (ADR-059 every-turn full-blob carry superseded for the retrieved-NPC channel, per ADR-118).

**Reuse note (pragmatic-restraint):** zero new production surface — the suite reuses the live embedding/cosine machinery, the real handler delegate, real `Orchestrator.build_narrator_prompt`, and the existing `test_seed_valley_injection.py` / `test_universal_retrieval_dispatch.py` patterns. Exactly right for a capstone: no new code, only proof.

**Decision:** Proceed to verify (TEA). No hand-back to Dev — the single mismatch is trivial spec-text drift (AC7) resolved by clarification, not a code defect.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (6/6), ruff clean, **pyright 0 errors** (cleared 4 pre-existing), dispatch dir 172 passed / 17 skipped (no regression).

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 1 (`tests/server/dispatch/test_universal_retrieval_e2e.py` — the only changed file)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 4 findings | 3 high (extract `_UnavailableDaemon`/`_make_orchestrator`/`_FakeSocket` to shared conftest), 1 medium (`_install_span_exporter` helper) |
| simplify-quality | 2 findings | 2 medium (missing type annotations on `_retrieval_span`, `_valley_section_names`) |
| simplify-efficiency | 4 findings | 1 high (merge the two daemon mocks), 2 medium (span-attr test "redundant"; inline `_install_span_exporter`), 1 low (`_retrieval_span` parallels 75-7 — intentional) |

**Applied (2):**
- Annotated private helpers: `_valley_section_names(registry: PromptRegistry, ...)`.
- Refactored `_retrieval_span -> _retrieval_span_attrs`, returning the asserted-non-None span attributes (`Mapping[str, Any]`). This implements the quality teammate's type-safety finding *and* clears 4 **pre-existing** pyright `reportOptionalMemberAccess` errors on `span.attributes.get(...)` (verified present on the committed `4cc6812f` before this pass — not a regression I introduced). Committed `910a95b6`.

**Declined high-confidence findings (with rationale — judgment over rote application):**
- *Extract `_UnavailableDaemon` / `_make_orchestrator` / `_FakeSocket` to shared `tests/server/conftest.py`* — **out of scope.** This is a test-only verification story touching ONE file; moving helpers into shared conftest expands the diff to shared fixtures and would leave the duplication un-deduped on the sibling side (`test_universal_retrieval_dispatch.py`, `test_seed_valley_injection.py`) unless those are refactored too. That is a separate cross-file cleanup, filed below as a non-blocking Improvement.
- *"Rely on conftest autouse daemon guard instead of the local `_UnavailableDaemon`"* — **rejected (correctness risk).** The test patches `sidequest.game.retrieval_orchestration.DaemonClient` at its construction site (orchestrator.py:240 `client = DaemonClient()`); I will not trade an explicit, verified patch for an unverified claim that the autouse guard covers that exact reference (measure, don't assert).
- *Merge `_FakeDaemon` + `_UnavailableDaemon` into one parametrized `_MockDaemon(available=...)`* — **declined (lateral).** The two intention-revealing named classes read better at call sites than `_MockDaemon(available=False)`; merging trades clarity for fewer lines.

**Dismissed (medium):** efficiency's "span-attributes test is redundant" — **false.** The span-attributes test pins AC6 (OTEL observability from a REAL fill through the production delegate); the headline test pins AC5 (Valley injection); 75-7's span test uses a SYNTHETIC crafted `RetrievedEntities`. Three distinct surfaces, not redundant. `_install_span_exporter` inline-vs-extract (medium, conflicting advice) — left as-is (2 call sites, fine).

**Reverted:** 0.

**Overall:** simplify: applied 2 fixes (type-safety); structural-extraction findings deferred to a future cross-file cleanup story.

**Quality Checks:** All passing (ruff format/check, pyright 0 errors, pytest 6/6 + dispatch dir green).
**Handoff:** To Reviewer (Granny Weatherwax) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (6/6 tests, 172 dispatch-dir, ruff PASS, pyright 0, 0 smells) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (1 enabled subagent returned clean; 8 disabled via `workflow.reviewer_subagents` and pre-filled as Skipped)
**Total findings:** 0 confirmed, 0 dismissed, 1 deferred (TEA's cross-file conftest-extraction Improvement — out of scope, agreed)

Note: only `preflight` is enabled in `workflow.reviewer_subagents`; the thematic subagents are operator-disabled. I performed their domains (test-quality, type-design, silent-failure, simplify) myself by hand below.

## Reviewer Assessment

**Verdict:** APPROVED

A test-only change: one new file `sidequest-server/tests/server/dispatch/test_universal_retrieval_e2e.py` (+406), no production code touched. This is the capstone e2e wiring test for Epic 75 (ADR-118). I read every line myself and hand-covered the disabled thematic domains.

### Observations (hand-review; ≥5)

1. **[VERIFIED] No source-text wiring tests (server CLAUDE.md "No Source-Text Wiring Tests").** Every assertion is behavioural — the returned `RetrievedEntities`, the `retrieval.universal` span attributes, the registered Valley `PromptSection`, a real `watcher_hub` subscriber. No `read_text()`/regex on source anywhere. Evidence: file has zero `.read_text(` / `re.` usage; assertions at lines 191-194, 225-247, 269-273, 299-312, 344-348, 397-404.
2. **[VERIFIED] Real production seam, not a synthetic no-op (the #1 trap).** Every test enters via `handler._retrieve_entities_for_turn(sd, action)` (lines 189, 222, 267, 298, 342, 386) — the live delegate — never a direct `retrieve_turn_context()` construction. The capstone's net-new value (Valley injection) is proven via the real `_build_turn_context` + a real `Orchestrator.build_narrator_prompt` (lines 230-247).
3. **[VERIFIED] Test quality — no vacuous assertions ([TEST] domain, hand-covered).** Every `assert` checks a concrete value: `result.outcome == "success"`, specific card id membership, `"wandering minstrel" in npc_sections[0].content`, `attrs.get("retrieval.npc_count") == 1`, absence of `retrieved_locations`/`retrieved_factions` from the Valley set. No `assert True`, no lone-truthy, no `is_none()` on always-None. The `is None` checks (lines 299-304) are meaningful contract checks (the value could be a populated list if the zero-byte-leak contract broke).
4. **[VERIFIED] Type design / pyright clean ([TYPE] domain, hand-covered).** All helpers annotated; `_retrieval_span_attrs` asserts non-None and returns a narrowed `Mapping[str, Any]` (lines 152-163) — pyright reports 0 errors (preflight confirms). The verify-phase refactor cleared 4 pre-existing `reportOptionalMemberAccess` errors.
5. **[VERIFIED] Silent-failure domain ([SILENT], hand-covered).** No swallowed exceptions in the test. `_UnavailableDaemon.embed` raises loudly with `# pragma: no cover` (line 94, correctly never reached). The fixtures force deterministic outcomes (`query_failed` / `success`) rather than masking failures.
6. **[VERIFIED] Floor-vs-fill dedup correctness.** `test_floor_npc_not_double_injected_into_fill` (lines 321-348): Borin stamped scene-present (last_seen_turn=5, interaction=5 → floored), his `npc:borin` card seeded in `entity_store`, asserted EXCLUDED from the fill while the off-stage `npc:wandering_minstrel` fills. The id convention (`npc:{casefold/underscore}`) matches `_floor_card_ids` and `EntityCard.new`. Correct and non-trivial.
7. **[LOW] Polling loop in the watcher-hub test (lines 388-396)** — 50×10ms poll waiting for the async broadcast is a mild flake-risk under heavy load, but it breaks early on success and is the exact proven pattern from the 75-7 sibling (`test_universal_retrieval_dispatch.py`). Not blocking.
8. **[LOW] Three test-local helpers duplicate sibling/conftest patterns** (`_make_orchestrator`, `_FakeSocket`, unavailable-daemon stub) — already logged by TEA as a deferred cross-file cleanup Improvement. Out of scope for a one-file test-only story. Not blocking.

### Rule Compliance (lang-review/python.md — applied to the test file)
- **#1 Silent exceptions:** Compliant — no bare/swallowing except; the one `raise` is an intentional guard.
- **#3 Type annotations:** Compliant — all helper signatures + returns annotated (the file's whole point of the verify pass).
- **#6 Test quality:** Compliant — no vacuous assertions; mock targets are the import sites actually used (`sidequest.game.retrieval_orchestration.DaemonClient`/`.tracer`), not where-defined; every test has meaningful assertions; no `@pytest.mark.skip`.
- **#9 Async pitfalls:** Compliant — every coroutine awaited; `@pytest.mark.asyncio` on all async tests; no blocking calls in async bodies.
- **#10 Import hygiene:** Compliant — explicit imports, no star imports; `from collections.abc import Mapping` correct.

### Devil's Advocate

Suppose I want this code to be broken. Where would it hide?

*"The tests pass but prove nothing."* — This is the gravest charge for a GREEN-on-arrival capstone. But it doesn't hold: the tests enter via the real `handler._retrieve_entities_for_turn` and assert a real `Orchestrator.build_narrator_prompt` registers the Valley section. I confirmed (by reading retrieval_orchestration.py, session_helpers.py:1144-1156, orchestrator.py:2137-2156) that this is the genuine production path. If 75-5's floor+fill or the orchestrator's `if section_body:` registration regressed, `test_capstone_action_to_fill_to_valley_npc_section` would fail. The suite even demonstrated it CAN fail — TEA's first run failed against the mocked `sd.orchestrator`. So these are not tautologies.

*"The fixed embedding vector is a cheat."* — A skeptic could argue cosine 1.0 from an identical vector doesn't exercise real ranking. True, but ranking math is 75-5's unit-test concern; this capstone's job is *wiring reachability + injection*, for which a deterministic offline fill is exactly right (and avoids daemon/MiniLM flakiness). The similarity-floor/budget edge cases live in `tests/game/test_retrieval_orchestration.py`.

*"A confused maintainer breaks it on refactor."* — Because assertions are behavioural (span fired, section registered, event delivered), a harmless rename of internals won't break them; only a real wiring break will. That is the correct fragility profile.

*"Race/flake under load."* — The watcher-hub poll (500ms ceiling) is the only timing-dependent spot; it mirrors the proven 75-7 pattern and exits early. Flagged Low. Nothing here corrupts state or leaks across tests (monkeypatch + try/finally unsubscribe restore everything).

No new finding emerged that changes the verdict. No Critical/High. The change is a disciplined, well-documented, behaviour-driven test that strengthens Epic 75's wiring guarantee with zero production risk.

**Data flow traced:** player action string → `handler._retrieve_entities_for_turn` → `retrieve_for_turn` → `retrieve_turn_context` (floor+fill, span) → `_build_turn_context` (typed render) → `build_narrator_prompt` (Valley registration) — assertions land at each hop. Safe.
**Pattern observed:** behaviour-driven wiring test mirroring `test_universal_retrieval_dispatch.py` + `test_seed_valley_injection.py` — `tests/server/dispatch/test_universal_retrieval_e2e.py:1-407`.
**Error handling:** test forces deterministic outcomes; `_UnavailableDaemon.embed` fails loud (no swallow).
**Handoff:** To SM for finish-story.

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-03T06:18:22Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-03 | 2026-06-03T05:48:56Z | 5h 48m |
| red | 2026-06-03T05:48:56Z | 2026-06-03T06:00:47Z | 11m 51s |
| green | 2026-06-03T06:00:47Z | 2026-06-03T06:02:57Z | 2m 10s |
| spec-check | 2026-06-03T06:02:57Z | 2026-06-03T06:04:40Z | 1m 43s |
| verify | 2026-06-03T06:04:40Z | 2026-06-03T06:12:52Z | 8m 12s |
| review | 2026-06-03T06:12:52Z | 2026-06-03T06:17:09Z | 4m 17s |
| spec-reconcile | 2026-06-03T06:17:09Z | 2026-06-03T06:18:22Z | 1m 13s |
| finish | 2026-06-03T06:18:22Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): The universal-retrieval pipeline (ADR-118, Epic 75) is correctly wired end-to-end — the capstone tests are GREEN-on-arrival, so this story carries no Dev implementation. Affects `sidequest-server/tests/server/dispatch/test_universal_retrieval_e2e.py` (verification artifact only). SM may consider that future "capstone wiring test" stories for already-merged epics fit the `trivial` workflow better than `tdd`, since there is no RED→GREEN cycle. *Found by TEA during test design.*
- **Question** (non-blocking): The fixture `session_handler_factory` provides `sd.orchestrator` as `MagicMock(spec=Orchestrator)`, so any e2e test that needs the real prompt-assembly half (`build_narrator_prompt`) must construct its own `Orchestrator()`. This is fine and documented, but a future shared helper (real-orchestrator-on-demand) would reduce per-test boilerplate. Affects `sidequest-server/tests/server/conftest.py`. *Found by TEA during test design.*

### Dev (implementation)
- No upstream findings during implementation. Confirmed Igor's GREEN-on-arrival finding: the ADR-118 pipeline is correctly wired; no production gap surfaced. *Found by Dev during implementation.*

### TEA (test verification)
- **Improvement** (non-blocking): Three test helpers duplicate across the dispatch/agents suites and could be hoisted to shared `conftest.py`: `_make_orchestrator` (also in `tests/agents/test_seed_valley_injection.py`), `_FakeSocket` (also in `tests/server/dispatch/test_universal_retrieval_dispatch.py`), and the unavailable-daemon stub (conftest already has `_UnavailableDaemonClient`). Affects `sidequest-server/tests/server/conftest.py` (+ the two sibling test files). Deferred from 75-8 as out-of-scope cross-file cleanup. *Found by TEA during test verification.*

### Reviewer (code review)
- No upstream findings during code review. The change is a clean, behaviour-driven, test-only capstone; preflight green (6/6, pyright 0, ruff PASS, 0 smells), no Critical/High. I corroborate TEA's deferred conftest-extraction Improvement but add nothing blocking. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Prompt-assembly half driven by a fresh `Orchestrator()` rather than `sd.orchestrator`**
  - Spec source: context-story-75-8.md, "Technical Guardrails" / AC-1 (drive the production delegate `handler._retrieve_entities_for_turn`)
  - Spec text: "Enter via the production delegate `handler._retrieve_entities_for_turn` … assert the retrieved fill actually lands as a Valley PromptSection"
  - Implementation: the RETRIEVAL half runs through the real handler delegate as specified; the final PROMPT-ASSEMBLY assertion (`build_narrator_prompt` → Valley registry) uses a fresh real `Orchestrator()` because `session_handler_factory` deliberately mocks `sd.orchestrator` (`MagicMock(spec=Orchestrator)`).
  - Rationale: the fixture isolates the handler from the narrator; the canonical project pattern for Valley-registration assertions (`tests/agents/test_seed_valley_injection.py`) builds a real `Orchestrator()`. The chain stays faithful end-to-end — only the prompt assembler is a real (not mocked) instance.
  - Severity: minor
  - Forward impact: none — `build_narrator_prompt` is backend-agnostic for the entity-section registrations under test.

### Dev (implementation)
- No deviations from spec. No production code was written (test-only verification story); the TEA test suite passes unmodified.

### Reviewer (audit)
- **TEA's "fresh `Orchestrator()` for the prompt-assembly half"** → ✓ ACCEPTED by Reviewer: sound and unavoidable — `session_handler_factory` ships `sd.orchestrator` as `MagicMock(spec=Orchestrator)`, so the Valley-registration assertion must use a real `Orchestrator()`; this matches the canonical `test_seed_valley_injection.py` pattern and the retrieval half still runs through the real handler delegate. No fidelity loss.
- **Dev "no deviations"** → ✓ ACCEPTED by Reviewer: correct — a test-only verification story; zero production code is the right outcome under Minimalist Discipline.
- No undocumented deviations found. I traced every assertion to a real production seam; the test does what the spec/ACs require, nothing diverges.

### Architect (reconcile)

Reviewed all prior entries against the spec sources (`sprint/context/context-story-75-8.md`, `sprint/context/context-epic-75.md`, ADR-118, sibling Epic-75 story ACs in `sprint/epic-75.yaml`). The TEA, Dev, and Reviewer-audit entries are accurate, with all 6 fields substantive — no corrections needed. One additional deviation, promised during spec-check, is formalized here:

- **AC-7 names a `to_card()` method that does not exist in the codebase**
  - Spec source: `sprint/context/context-story-75-8.md` (and `.session/75-8-session.md`) AC-7
  - Spec text: "EntityCard `to_card()` projectors for NPC, location, and faction are called in the retrieval path; the content field is embeddable and not a data dump."
  - Implementation: there is no `EntityCard.to_card()` method. Projection is performed by module-level functions `project_npc_card` / `project_location_card` / `project_faction_card` (`sidequest/game/entity_card.py:173/196/212`), invoked on the entity-sync path (75-4/75-6); `retrieve_turn_context` consumes already-projected, already-embedded cards from `sd.entity_store`. The test asserts the projected `content` reaching the Valley section (a behaviour check), correctly NOT asserting a `to_card()` call.
  - Rationale: the `to_card()` wording is an artifact of ADR-118 §D3's prose ("each entity type provides a `to_card()` projector"), which the 75-4 implementation realized as standalone module functions rather than a method. The AC was derived from that prose (the story YAML carried no ACs). The code and test are correct; the AC text is the inaccuracy. SM flagged this at setup, TEA encoded the correct shape, Architect confirmed it at spec-check. Resolution = clarify spec (Option C); no code change.
  - Severity: trivial (documentation/wording only)
  - Forward impact: none. Note for future ADR-118 authors: if a literal `to_card()` method is ever desired for ergonomics, it would be a thin wrapper over the existing `project_*_card` functions — not a behavioural change.

- No other undocumented deviations. AC accountability: all 8 ACs are DONE (covered by the 6-test suite per the TEA AC→test map); none deferred or descoped, so no deferral justifications require cross-referencing.