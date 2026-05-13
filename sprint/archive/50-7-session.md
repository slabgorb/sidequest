---
story_id: "50-7"
jira_key: null
epic: "50"
workflow: "tdd"
---

# Story 50-7: Scenario: GossipEngine — two-phase belief propagation, contradiction detection, credibility decay

## Story Details

- **ID:** 50-7
- **Title:** Scenario: GossipEngine — two-phase belief propagation, contradiction detection, credibility decay
- **Jira Key:** None (SideQuest never uses Jira)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 8
- **Priority:** p2
- **Type:** feature

## Acceptance Criteria

1. GossipEngine implements two-phase belief propagation:
   - **Phase 1 (transmission):** Gossip from one NPC to another, subject to credibility and topic filters
   - **Phase 2 (integration):** Receiver evaluates and updates their belief state; contradictions trigger dispute resolution

2. Contradiction detection triggers when:
   - New gossip contradicts an existing belief (same fact, opposing value or disposition shift)
   - Credibility of source vs. existing belief holder is weighed
   - Integration can result in: acceptance, retention, or belief downgrade to "rumor" tier

3. Credibility decay system:
   - Gossip credibility degrades with each transmission hop (decay_per_hop parameter)
   - Source credibility (NPC reputation, prior accuracy) factors into propagation decisions
   - OTEL SPAN_GOSSIP_PROPAGATION emits at each step with credibility_before, credibility_after, accepted

4. Integration test covers:
   - Two-NPC chain (A→B transmits a fact; B updates belief state)
   - Contradiction case (A→B transmits opposite of B's existing belief)
   - Credibility downgrade (low-credibility source gossip lands as "rumored" not "known")
   - Multi-hop propagation (A→B→C, credibility decays twice)

5. OTEL observability shows belief state mutations on the GM dashboard:
   - SPAN_GOSSIP_PROPAGATION fires on each transmission with source, target, fact, credibility_before/after
   - SPAN_BELIEF_STATE_MUTATION fires when target NPC's belief state changes due to gossip
   - Residual contradiction cases are logged so no gossip is silently dropped

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-13T20:16:33Z
**Round-Trip Count:** 1

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-13T17:34:43Z | 2026-05-13T17:36:04Z | 1m 21s |
| red | 2026-05-13T17:36:04Z | 2026-05-13T17:43:28Z | 7m 24s |
| green | 2026-05-13T17:43:28Z | 2026-05-13T18:02:49Z | 19m 21s |
| spec-check | 2026-05-13T18:02:49Z | 2026-05-13T18:35:57Z | 33m 8s |
| verify | 2026-05-13T18:35:57Z | 2026-05-13T19:24:39Z | 48m 42s |
| review | 2026-05-13T19:24:39Z | 2026-05-13T19:53:27Z | 28m 48s |
| red | 2026-05-13T19:53:27Z | 2026-05-13T19:59:28Z | 6m 1s |
| green | 2026-05-13T19:59:28Z | 2026-05-13T20:03:41Z | 4m 13s |
| spec-check | 2026-05-13T20:03:41Z | 2026-05-13T20:05:42Z | 2m 1s |
| verify | 2026-05-13T20:05:42Z | 2026-05-13T20:10:24Z | 4m 42s |
| review | 2026-05-13T20:10:24Z | 2026-05-13T20:16:33Z | 6m 9s |
| finish | 2026-05-13T20:16:33Z | - | - |

## Delivery Findings

No upstream findings at setup phase.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): ADR-053 names two telemetry constants the engine must emit (`SPAN_GOSSIP_PROPAGATION`, `SPAN_BELIEF_STATE_MUTATION`) but neither exists in `sidequest/telemetry/spans/scenario.py` today. Affects `sidequest/telemetry/spans/scenario.py` (Dev must add both constants and register them in `FLAT_ONLY_SPANS` or `SPAN_ROUTES`). *Found by TEA during test design.*
- **Gap** (non-blocking): No production caller invokes `GossipEngine.propagate()` yet — story 50-7 scope is the engine itself, not the per-turn invocation site. The downstream wiring (likely from `session.py`'s between-turn pipeline, currently dark per `session.py:698`) is out of scope for this story but is a known follow-up under ADR-087's P2 RESTORE bundle. Affects future story (not 50-7). *Found by TEA during test design.*
- **Question** (non-blocking): The "downgrade to rumored" language in AC2 maps naturally to `BeliefSuspicion` or to `BeliefClaim(believed=False)`; tests assert the negative ("never promotes to BeliefFact") rather than dictating which variant Dev picks, leaving the implementation choice open. If Dev wants the test to lock a specific variant, escalate during GREEN. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): The engine has no production caller — confirmed during GREEN. `GossipEngine.propagate()` is wired into the scenario module namespace and reachable from tests, but no `session.py` / between-turn pipeline hook invokes it yet. Affects `sidequest/game/session.py` and the scenario tick path (a follow-up restoration story must call `propagate()` from the live between-turn loop, otherwise this is dead code in production). *Found by Dev during implementation.* — escalates the TEA-flagged gap from non-blocking to actionable for the next 50-* story in the gossip/accusation chain.
- **Improvement** (non-blocking): The engine currently storages ALL gossip-arrived beliefs as `BeliefSuspicion` (rumor tier) regardless of credibility. A future tuning pass could promote very-high-credibility gossip (e.g. ≥0.9 post-decay from a trusted source) to `BeliefClaim(believed=True)` so the narrator gets a stronger signal that an NPC takes the gossip seriously. Affects `sidequest/game/gossip_engine.py` (`propagate` phase 2 branch). No urgency — Suspicion's confidence float carries the same information in a single variant. *Found by Dev during implementation.*

### TEA (test verification)
- **Improvement** (non-blocking): The `_events_named` / `_spans_named` filter-by-name helpers in `tests/game/test_gossip_engine.py` duplicate near-identical inline filters across 7+ test files (`test_npc_observation_gate.py`, `test_orbital_beats.py`, `test_scrapbook_coverage.py`, etc.). A shared `tests/_helpers/otel.py` module would consolidate, but the refactor reaches outside this story's diff. Affects all OTEL-asserting test files. *Found by TEA during test verification.*
- **Improvement** (non-blocking): `_sender_confidence(sender, subject)` in `sidequest/game/gossip_engine.py` performs an isinstance-dispatch over BeliefFact/BeliefSuspicion/BeliefClaim to extract the strongest confidence. This logic may recur in story 50-8 (AccusationEvaluator), narrator context building, or clue-graph reasoning. Promoting it to `BeliefState.max_confidence(subject) -> float | None` (public method on the existing belief-state module) would centralize the dispatch. Affects `sidequest/game/belief_state.py` (new method) + `sidequest/game/gossip_engine.py` (becomes a one-line delegation). Defer until 50-8 confirms it needs the helper. *Found by TEA during test verification.*
- **Improvement** (non-blocking): Two pre-existing lint warnings surfaced during full-tree `ruff check .` (`tests/game/test_session_time_skip.py`, `tests/integration/test_trope_time_skip_e2e.py` — both story 50-4 files). Both are auto-fixable import-order issues unrelated to 50-7's diff. Affects those two files. Not in 50-7 scope. *Found by TEA during test verification.*

### Reviewer (code review)

- **Gap** (non-blocking): `tests/server/test_chargen_dispatch.py::TestSliceAWiring::test_caverns_delver_loadout_wired_into_snapshot` exhibits a pre-existing flake in isolation (~13% failure rate across 15 isolated runs on this branch; chargen test file is not modified by 50-7). The failure shows duplicate items in the kit roll (3 torches, 3 waterskins, 2 iron_spikes) and missing `rations_day` — consistent with a `random` module state issue. The preflight subagent observed this once during the 50-7 combined run and misattributed it to gossip-test ordering; my independent reproduction confirms it occurs without the gossip test file involved. Affects `tests/server/test_chargen_dispatch.py` and likely the C&C kit-roll code path that consumes Python's global `random` state without seeding. Out of 50-7 scope; should become its own bugfix story. *Found by Reviewer during code review.*
- **Gap** (non-blocking): The engine's silent acceptance of unknown `from_npc` (gossip_engine.py:159) was the load-bearing reject finding for this review. Future stories that wire `GossipEngine.propagate()` into the session pipeline (ADR-087 P2 RESTORE) MUST exercise the `from_npc not in npcs` path explicitly — either the engine raises (preferred for consistency with `to_npc`) or the upstream caller pre-filters transmissions whose `from_npc` is not in the session's NPC registry. The current asymmetric behavior is a footgun for the wiring story. Affects `sidequest/game/gossip_engine.py:159-166` and the future per-turn invocation site. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): No test asserts the parent-child OTEL nesting between `SPAN_GOSSIP_PROPAGATION` and `SPAN_BELIEF_STATE_MUTATION` (the engine docstring at line 26-28 advertises nesting; tests check existence, not parent linkage). A future enrichment to `tests/game/test_gossip_engine.py` should assert `mutation_spans[0].parent.span_id == propagation_spans[0].context.span_id` so a refactor that un-nests the spans is caught. Affects `tests/game/test_gossip_engine.py` (test enrichment, not 50-7 blocker). *Found by Reviewer during code review.*
- **Question** (non-blocking): The `_events_named` helper at gossip_engine test file line 41 is unused — it filters span events by name, but no test calls it (only `_spans_named` is referenced in the test bodies). Either the helper was inherited from a copy-paste pattern and should be removed, or a test that was intended to use it is missing. Worth a brief check next time someone touches this file. Affects `tests/game/test_gossip_engine.py:41-45`. *Found by Reviewer during code review.* — **RESOLVED in round-trip 1**: TEA removed the unused helper during red rework.

### Reviewer (code review — round-trip 2)

- **Improvement** (non-blocking): `bert.update_credibility("Alice", 0.5)` in `test_propagate_rejects_unknown_from_npc` is unused — the engine raises before reading credibility. The setup line implies the credibility value matters to the test path, but it does not. Affects `tests/game/test_gossip_engine.py` (the new from_npc-raise test). Delete the line, or replace with a comment noting the setup is intentionally minimal. *Found by Reviewer (test-analyzer) during round-trip 2 review.*
- **Improvement** (non-blocking): Five test methods import `SPAN_GOSSIP_PROPAGATION` / `SPAN_BELIEF_STATE_MUTATION` inline inside their function bodies (lines 438, 483, 523, 567, 616). `TestWiring` correctly hoists these constants to the top-level import block. Inconsistency violates python lang-review rule #10 (import hygiene). Affects `tests/game/test_gossip_engine.py`. Hoist the imports during the next adjacent edit. *Found by Reviewer (test-analyzer + rule-checker) during round-trip 2 review.*
- **Improvement** (non-blocking): `attrs.get("contradicted") is True` on line 602 uses `.get()` while every other span-attribute check in the rework now uses direct key access (`attrs["key"]`). Inconsistent diagnostic surface — a missing key produces `None is True` (False) rather than a clearer `KeyError`. Affects `tests/game/test_gossip_engine.py:602`. Change to `attrs["contradicted"] is True` for consistency. *Found by Reviewer (rule-checker) during round-trip 2 review.*
- **Improvement** (non-blocking): The `propagate()` method docstring at `gossip_engine.py:143-148` describes the Phase 2 storage gate as "if credibility is positive, append a BeliefSuspicion" but does not explicitly note that the same gate covers the contradiction sub-case. The module docstring (lines 14-21) does cover the contradiction sub-case, but a reader of only the method docstring lacks the cross-reference. Affects `sidequest/game/gossip_engine.py:143-148`. Append one clause to the Phase 2 sentence explicitly noting that contradicting gossip with positive credibility lands as a Suspicion alongside the preserved Fact. *Found by Reviewer (comment-analyzer) during round-trip 2 review.*

## Impact Summary

### Engineering Impact

**2 findings escalated from non-blocking to forward-actionable:**
1. **Production wiring gap** (ADR-087 P2 RESTORE) — `GossipEngine.propagate()` currently has no per-turn caller in `session.py`. The between-turn pipeline (`session.py:698`) is dormant and must invoke the engine in a future restoration story; otherwise this becomes dead code in production.
2. **Fallback asymmetry footgun** — The engine now raises `KeyError` for unknown `to_npc` AND unknown `from_npc` (symmetric). The future wiring story MUST pre-filter transmissions from off-scene or unregistered NPCs, or handle the raise explicitly, to avoid run-time failures.

### Test Coverage & Verification

**Test suite health:** 24 tests across 6 classes covering all 5 ACs.
- AC4's 4 integration scenarios each have a dedicated test (two-NPC chain, contradiction, credibility downgrade, multi-hop).
- OTEL observability tested: SPAN_GOSSIP_PROPAGATION + SPAN_BELIEF_STATE_MUTATION emission asserted with exact attribute values; parent-span nesting also asserted via `parent.span_id == context.span_id`.
- Conditional contradiction storage (positive credibility → Suspicion, zero credibility → not stored) locked by `test_contradicting_gossip_with_zero_credibility_is_not_stored`.
- Input validation tested across 5 variants (empty subject/content/from_npc, self-loop, unknown to_npc/from_npc).

**Quality gates:** 5238/5238 server tests passing, lint clean on all 3 modified files, pyright clean, ruff format clean.

**Wiring verification:** Engine importable from `sidequest.game.gossip_engine` with `__all__` exports. Both new telemetry constants (`SPAN_GOSSIP_PROPAGATION`, `SPAN_BELIEF_STATE_MUTATION`) registered in `FLAT_ONLY_SPANS`. Session-pipeline integration deferred to ADR-087 P2 RESTORE per Architect spec-check ruling.

### Design Decisions Logged

**5 deviations accepted by Reviewer across both rounds:**
1. All gossip stored uniformly as `BeliefSuspicion` (single variant) — simplifies multi-hop lineage lookup; forward-compatible with `AccusationEvaluator` (50-8) via `BeliefSourceToldBy` discriminator.
2. Empty-string validation enforced at Pydantic constructor (not engine entry) — matches `belief_state.py` idiom; single source of truth.
3. `contradiction_threshold` parameter not implemented — TEA contract's ellipsis was advisory; no test demanded the parameter; "No Stubbing" applies.
4. Wiring test scope is namespace-level, not session-pipeline-level — Architect explicitly ruled the production-caller gap is deferred to ADR-087 P2.
5. **Unknown `from_npc` raises `KeyError` (option A chosen in round-trip 1)** — symmetric to `to_npc` handling; honors CLAUDE.md "No Silent Fallbacks" (which the engine's own docstring self-cites); least-surprise principle.

### Non-Blocking Follow-Ups (4 Improvements)

Logged in Delivery Findings, eligible for adjacent fixes on next-story touches to this file:
1. **OTEL helper consolidation** — `_spans_named` duplicated across 7+ test files; propose shared `tests/_helpers/otel.py`.
2. **Confidence lookup refactor** — `_sender_confidence()` dispatch may recur in 50-8; consider `BeliefState.max_confidence(subject)` public method.
3. **Test import hygiene** — 5 methods import `SPAN_*` constants inline; hoist to top-level (python lang-review rule #10).
4. **Span-attribute access consistency** — Line 602 uses `.get()` while others use `attrs["key"]`; align for clearer KeyError on missing key.

Plus 1 documentation improvement: `propagate()` method docstring should cross-reference the contradiction sub-case the module docstring now covers (~1 sentence).

### Integration Readiness

- **Prerequisite satisfied:** discover_clue wiring (50-5) shipped; belief-state infrastructure reachable.
- **Downstream consumer:** 50-8 (AccusationEvaluator) will consume gossip-propagated belief states; current Suspicion-only storage is forward-compatible.
- **Reference content:** `tea_and_murder` genre pack (recruitment, scandal, social reputation gossip).
- **Production activation path:** ADR-087 P2 RESTORE story must add the between-turn invocation site.
- **Pre-existing chargen test flake** (~13% rate in isolation, unrelated to this branch) was independently observed and reattributed during round-trip 0 — should become its own bugfix story.

### Review Outcome

- **Round-trip 0:** REJECTED (3 HIGH + 4 MEDIUM + 2 LOW)
- **Round-trip 1:** TEA red rework → Dev green rework → Architect spec-check (Aligned) → TEA verify (clean)
- **Round-trip 2:** APPROVED (0 blockers; 4 non-blocking Improvements logged for future adjacent fixes)

## Design Deviations

No deviations logged at setup phase.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Multi-hop lineage assertion uses inequality, not exact arithmetic**
  - Spec source: session file AC4 (`Multi-hop propagation (A→B→C, credibility decays twice)`)
  - Spec text: "Multi-hop propagation (A→B→C, credibility decays twice)"
  - Implementation: `test_multi_hop_decays_more_than_single_hop` asserts `credibility_after < 0.7` rather than a precise value like `0.5`. This leaves Dev free to choose whether multi-hop tracking is via stored-belief confidence lookup or an explicit hops counter on the transmission.
  - Rationale: AC4 says "decays twice" without specifying the exact arithmetic. A strict-inequality test forces the engine to track lineage (without it, the multi-hop test would not fail with a naive single-hop subtraction), but does not force a specific tracking mechanism.
  - Severity: minor
  - Forward impact: Reviewer should confirm the chosen lineage mechanism is sensible during code review; the test is intentionally permissive on the *how* and strict on the *what*.

- **Wiring test is namespace-level, not session-pipeline-level**
  - Spec source: CLAUDE.md ("Every Test Suite Needs a Wiring Test", "Verify Wiring, Not Just Existence")
  - Spec text: "every set of tests must include at least one integration test that verifies the component is wired into the system — imported, called, and reachable from production code paths"
  - Implementation: `TestWiring` verifies the engine is importable from `sidequest.game.gossip_engine` with `__all__` exports and that both new span constants are registered in the telemetry catalog (so `tests/telemetry/test_routing_completeness.py` will not silently skip them). It does NOT exercise `session.py`'s between-turn pipeline because that pipeline is dormant (`session.py:698`) and out of story scope.
  - Rationale: Story 50-7 builds the engine itself. Wiring into the per-turn pipeline is ADR-087 follow-up work — a separate restoration slice. Asserting an integration that doesn't exist would be either a stub or a test that locks scope creep onto Dev.
  - Severity: minor
  - Forward impact: A follow-up story (the per-turn invocation site) MUST include a session-level integration test that calls `GossipEngine.propagate()` from production code. Surfaced in Delivery Findings as a non-blocking Gap.

- **Empty-string validation enforced at construction, not at engine entry**
  - Spec source: CLAUDE.md ("No Silent Fallbacks")
  - Spec text: "If something isn't where it should be, fail loudly. Never silently try an alternative path, config, or default."
  - Implementation: `TestInputValidation` asserts `pytest.raises(ValidationError)` on `GossipTransmission(subject="")` etc., requiring Dev to add pydantic validators (`min_length=1` constraint or equivalent) on the data class fields rather than checking at `propagate()` entry.
  - Rationale: Constructor-time validation matches the existing pattern in `belief_state.py` (e.g. `BeliefSuspicion.make` clamps confidence at construction) and means invalid transmissions never reach the engine. Engine-entry validation would be a redundant second pass; constructor validation is the single source of truth.
  - Severity: minor
  - Forward impact: none.

### Dev (implementation)
- **All gossip stored uniformly as BeliefSuspicion (rumor tier)**
  - Spec source: session AC2 (`Integration can result in: acceptance, retention, or belief downgrade to "rumor" tier`); TEA "Question" finding flagging the variant choice
  - Spec text: "belief downgrade to 'rumor' tier"
  - Implementation: `propagate()` phase 2 appends `BeliefSuspicion.make(..., confidence=cred_after)` for every accepted transmission regardless of credibility tier. No branch promotes to `BeliefClaim(believed=True)` even for very high credibility.
  - Rationale: A single-variant storage path keeps `_sender_confidence()` lookup uniform — multi-hop lineage tracking reads suspicion.confidence directly without a type switch. The `BeliefSuspicion.confidence` float carries the credibility signal the narrator needs without needing two variants. Single source of truth, simpler invariants.
  - Severity: minor
  - Forward impact: A follow-up tuning story may want to promote high-credibility gossip to `BeliefClaim` for narrator emphasis — surfaced as a non-blocking Improvement in Delivery Findings. Story 50-8 (AccusationEvaluator) consumes belief states and will need to read both variants; current Suspicion-only storage is forward-compatible.

- **`contradiction_threshold` constructor argument from TEA contract not implemented**
  - Spec source: session "Test contract summary (for Dev)" — `GossipEngine(self, *, decay_per_hop: float = 0.1, contradiction_threshold: float = ...)`
  - Spec text: "`contradiction_threshold: float = ...`" (ellipsis placeholder in the contract)
  - Implementation: `GossipEngine.__init__` accepts only `decay_per_hop`. No `contradiction_threshold` parameter.
  - Rationale: No test asserts the constructor accepts the second argument, and minimalist discipline (per agent definition) says don't add a parameter that no test demands. The TEA contract used `...` as a placeholder for future expansion — Dev read this as advisory, not load-bearing. Adding an unused parameter would be dead code per CLAUDE.md "No Stubbing".
  - Severity: minor
  - Forward impact: If a future story (e.g. 50-8 AccusationEvaluator) needs a configurable threshold for what counts as a contradiction-worth-flagging, it must be added there. Currently any BeliefFact mismatch on subject+content trips `contradicted=True`; threshold-based comparison is not implemented.

### TEA (red rework)

### Reviewer (audit — round-trip 2)

- All round-trip 1 deviations from TEA, Dev, and the previous TEA red-rework entry → ✓ ACCEPTED by Reviewer (round-trip 2): the unknown-`from_npc`→raise decision is implemented exactly as documented; no new deviations introduced by the rework; the conditional-storage docstring fix matches the code gate.

### TEA (red rework)

- **Unknown `from_npc` → raise `KeyError` (option A chosen)**
  - Spec source: Reviewer Assessment HIGH finding on silent fallback at `gossip_engine.py:159`; Reviewer offered options A (raise) or B (document + span attr + test the fallback)
  - Spec text: "Decide: (a) raise `KeyError` for unknown `from_npc` symmetric to `to_npc`... OR (b) document the design in the propagate docstring AND emit a span attribute..."
  - Implementation: `test_propagate_rejects_unknown_from_npc` asserts `pytest.raises(KeyError)` when `from_npc` is absent from `npcs`. Symmetric to the existing `test_propagate_rejects_unknown_to_npc`. Drives Dev to add an explicit existence check in `propagate()` mirroring lines 153-157.
  - Rationale: Picked A because (1) symmetric handling matches the principle of least surprise; (2) CLAUDE.md "No Silent Fallbacks" is binding and self-cited in the engine's own docstring; (3) no AC/Architect/Dev artifact requested off-scene-sender support; (4) if off-scene sender ever becomes a real game requirement, it should be an explicit opt-in flag, not a silent default; (5) the default 0.5 credibility-for-strangers is a meaningful semantic for *known* strangers (registered NPCs) — not a fallback for missing ones.
  - Severity: load-bearing (resolves Reviewer's HIGH)
  - Forward impact: The future wiring story (ADR-087 P2 RESTORE) MUST pre-filter transmissions whose `from_npc` is not in the session's registered NPC map — or it will hit this raise. Documented in Reviewer's Delivery Findings (already logged).

### Reviewer (audit)

- **Multi-hop lineage assertion uses inequality, not exact arithmetic** → ✗ FLAGGED by Reviewer: the permissive inequality leaves a gap — test-analyzer confirmed a rounding-bug refactor returning 0.69 would still pass. Tighten to `pytest.approx(0.5)`. Captured in main severity table as `[MEDIUM] [TEST]`.
- **Wiring test is namespace-level, not session-pipeline-level** → ✓ ACCEPTED by Reviewer: Architect's explicit ruling at session line 327 ("ADR-087's P2 RESTORE bundle covers this. Reviewer should NOT mark this as a blocker") binds this decision. TEA and Dev both already filed it as a non-blocking Delivery Finding. Honoring upstream ruling.
- **Empty-string validation enforced at construction, not at engine entry** → ✓ ACCEPTED by Reviewer: constructor-time validation matches `BeliefSuspicion.make`'s clamping idiom in `belief_state.py`. Single source of truth. Agrees with TEA's reasoning.
- **All gossip stored uniformly as BeliefSuspicion (rumor tier)** → ✓ ACCEPTED by Reviewer: simpler invariant, forward-compatible with story 50-8 via the `BeliefSourceToldBy` discriminator. Promoting high-credibility gossip to `BeliefClaim` is correctly logged as a non-blocking Improvement.
- **`contradiction_threshold` constructor argument from TEA contract not implemented** → ✓ ACCEPTED by Reviewer: TEA's ellipsis was advisory, no test demanded it, "No Stubbing" applies. Agrees with Dev's reasoning.

## Sm Assessment

**Scope:** Server-only TDD story for the scenario subsystem (ADR-053). Build GossipEngine with two-phase belief propagation, contradiction detection, and credibility decay. 8 points — large but well-bounded by 5 acceptance criteria.

**Upstream context for TEA:**
- ADR-053 (Scenario System — Clue Graph, Belief State, Gossip Propagation) is the governing spec; status is *partial* per DRIFT.md
- Prerequisite 50-5 (discover_clue wiring) shipped — belief-state infrastructure should be reachable
- Next story 50-8 (AccusationEvaluator) consumes gossip state — design with that downstream consumer in mind
- `tea_and_murder` genre pack is the reference content (recruitment, scandal, social reputation gossip)
- OTEL observability is **not optional** per the CLAUDE.md OTEL principle: SPAN_GOSSIP_PROPAGATION + SPAN_BELIEF_STATE_MUTATION must fire; residual contradictions logged, never silently dropped

**TEA focus areas:**
1. Test phase split (transmission vs. integration) explicitly — don't collapse to one round-trip
2. AC4 enumerates 4 integration scenarios (two-NPC chain, contradiction, credibility downgrade, multi-hop) — these are the load-bearing failing tests
3. OTEL span emission tests required per AC3 + AC5 — assert spans exist and carry credibility_before/credibility_after
4. Watch for stub temptation on belief-state lookup if the integration point isn't quite where you expect — wire to real state per CLAUDE.md "Wire Up What Exists"

**Risks:**
- ADR-053 partial status means scaffolding may exist in unexpected places — Architect consult possible during green if seams are unclear
- "Belief downgrade to rumored" requires KnownFact.confidence states — 50-17 promotes that to a Literal enum but isn't blocking; coordinate if TEA needs the enum first

**Branch:** `feat/50-7-gossip-engine-propagation` at `sidequest-server/` (base: develop)
**Next phase:** red → tea (The Caterpillar)

## TEA Assessment

**Tests Required:** Yes
**Reason:** New runtime engine for a partial ADR (053). Per CLAUDE.md "No Stubbing" + "Don't Reinvent — Wire Up What Exists": the data layer (`belief_state.py`, `scenario_state.py`) already exists; the engine connecting them does not. RED tests drive the engine into existence with a contract that locks behavior, not implementation.

**Test Files:**
- `sidequest-server/tests/game/test_gossip_engine.py` — 21 tests across 6 classes (655 LOC). Covers all 5 ACs + lang-review input-validation rules + wiring.

**Tests Written:** 21 tests covering 5 ACs (every AC has direct test coverage; AC4's four enumerated scenarios — two-NPC chain, contradiction, credibility downgrade, multi-hop — each have a dedicated test).
**Status:** RED (collection-blocked: `ModuleNotFoundError: No module named 'sidequest.game.gossip_engine'` — expected RED shape, no pre-existing breakage).

### Rule Coverage (Python lang-review)

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent exceptions | `test_propagate_rejects_unknown_to_npc` (raises rather than swallowing unknown receiver) | failing (module missing) |
| #6 test quality | self-checked: every test has at least one non-vacuous assertion; no `assert True`, no bare truthy checks where a value was meaningful, no `let _ =` analogue | passing (self-audit) |
| #11 input validation | `TestInputValidation` (5 tests): empty subject / empty content / empty from_npc / self-loop / unknown to_npc all raise at constructor or engine entry | failing (module missing) |

Other lang-review rules (#2 mutable defaults, #3 type annotations, #4 logging, #5 path handling, #7 resource leaks, #8 unsafe deserialization, #9 async, #10 import hygiene, #12 dependency hygiene, #14 cleanup ordering) are not applicable to this story's surface (no mutable defaults at risk, no I/O, no async path, no resource handles, no new dependencies, no one-shot lifecycle queue). Reviewer should re-evaluate on the Dev diff.

**Rules checked:** 3 of 14 applicable lang-review rules have direct test coverage; remainder are not-applicable to story surface and will be enforced by the lang-review gate on the Dev diff.
**Self-check:** 0 vacuous tests. Every test asserts a concrete value, exception type, span name, attribute, or state shape — no `is_some()`-style truthy checks on uninspected values.

### Test contract summary (for Dev)

The tests assume this public API for `sidequest.game.gossip_engine`:

```python
class GossipTransmission(BaseModel):
    from_npc: str           # min_length=1, != to_npc
    to_npc: str             # min_length=1
    subject: str            # min_length=1
    content: str            # min_length=1
    sentiment: Literal["corroborating", "contradicting", "neutral"] = "neutral"


class TransmissionOutcome(BaseModel):
    from_npc: str
    to_npc: str
    subject: str
    content: str
    credibility_before: float
    credibility_after: float
    accepted: bool
    contradicted: bool = False


class GossipResult(BaseModel):
    outcomes: list[TransmissionOutcome]


class GossipEngine:
    def __init__(self, *, decay_per_hop: float = 0.1, contradiction_threshold: float = ...) -> None: ...

    def propagate(
        self,
        *,
        npcs: dict[str, BeliefState],     # npc name -> BeliefState
        transmissions: list[GossipTransmission],
        current_turn: int = 0,
    ) -> GossipResult: ...
```

And these new constants in `sidequest/telemetry/spans/scenario.py`:

```python
SPAN_GOSSIP_PROPAGATION = "scenario.gossip_propagation"   # or similar — tests use the constant, not the literal
SPAN_BELIEF_STATE_MUTATION = "scenario.belief_state_mutation"
FLAT_ONLY_SPANS.update({SPAN_GOSSIP_PROPAGATION, SPAN_BELIEF_STATE_MUTATION})
```

Required span attributes per AC3/AC5:
- `SPAN_GOSSIP_PROPAGATION`: `credibility_before`, `credibility_after`, `accepted`, `from_npc`, `to_npc`, `contradicted` (when applicable)
- `SPAN_BELIEF_STATE_MUTATION`: must identify the mutated NPC via `npc` or `target_npc`

### Behavior invariants the tests lock in

1. **Single-source-of-truth outcomes:** one transmission in → exactly one outcome out. No silent drops, including when accepted=False or contradicted=True.
2. **Sender immutability:** `npcs[from_npc].beliefs` is never modified by `propagate()`. Gossip flows one-way.
3. **Snapshot-then-mutate within batch:** two transmissions in the same call read identical pre-batch credibility values, regardless of list order. This is the load-bearing AC1 guarantee.
4. **Existing Fact preservation:** contradicting gossip never removes or overwrites a `BeliefFact`. The receiver may store the contradiction as suspicion/claim, but the canonical fact stays canonical.
5. **Lineage tracking:** multi-hop A→B→C decays strictly more than the single-hop A→C trust delta. Naive `cred - decay_per_hop` per call does not satisfy this — Dev must read the source NPC's existing belief confidence on the subject (or carry an explicit hops counter on the transmission).
6. **Credibility floor at 0.0:** clamped, never negative.
7. **Input validation at construction:** empty `subject` / `content` / `from_npc`, plus self-loop (`from == to`), all raise `pydantic.ValidationError`. Engine entry validates that `to_npc` exists in `npcs`.

**Handoff:** To Dev (The White Rabbit) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/game/gossip_engine.py` — new 230-LOC module implementing `GossipTransmission`, `TransmissionOutcome`, `GossipResult`, `GossipEngine`, plus internal `_Snapshot`, `_sender_confidence`, `_has_contradicting_fact` helpers
- `sidequest-server/sidequest/telemetry/spans/scenario.py` — added `SPAN_GOSSIP_PROPAGATION` and `SPAN_BELIEF_STATE_MUTATION` constants, registered both in `FLAT_ONLY_SPANS`

**Tests:** 21/21 passing on the new `tests/game/test_gossip_engine.py`; 240 regression tests passing across the scenario-adjacent surface (`tests/game/test_belief_state.py`, `tests/game/test_scenario_state.py`, `tests/server/test_scenario_bind.py`, full `tests/telemetry/`). Routing-completeness lint passes for both new span constants. Lint clean.

**Branch:** `feat/50-7-gossip-engine-propagation` pushed to `origin`.

### Implementation Summary

1. **Two-phase mutation:** `propagate()` first walks all transmissions into a list of `_Snapshot` records (credibility readings + contradiction flag) with no side effects, then walks the snapshot list emitting spans and appending beliefs. The receiver's credibility dict is never read after phase 1 begins, so transmission order within the batch cannot influence other transmissions' `credibility_before` values.

2. **Lineage tracking via sender confidence lookup:** `_sender_confidence(sender, subject)` returns the strongest belief the sender holds about the subject (Fact=1.0, Suspicion=its confidence, Claim=1.0 if believed else 0.0, None if no belief). `credibility_before` is then `min(receiver_trust_in_sender, sender_confidence)`. This makes A→B→C decay strictly more than A→C: by the time Bert relays to Carol, Bert's stored Suspicion has confidence 0.7 (from turn 1), capping turn 2's `credibility_before` at 0.7 instead of Carol's full 0.9 trust in Bert.

3. **Rumor-tier storage:** All accepted gossip lands as `BeliefSuspicion` with `confidence = credibility_after`. Never promoted to `BeliefFact`. Existing `BeliefFact` records are preserved verbatim — contradicting gossip is appended as low-confidence Suspicion alongside the canonical Fact, surfacing the dispute to the narrator without rewriting truth.

4. **Contradiction visibility:** `_has_contradicting_fact()` checks only for `BeliefFact` records with the same subject but different content. The flag rides on the outcome AND the `SPAN_GOSSIP_PROPAGATION` span attrs (`contradicted: True`). Rejected gossip (cred_after clamped to 0.0) still emits the propagation span — no silent drops.

5. **Constructor-time validation:** `GossipTransmission` uses pydantic `Field(min_length=1)` on `from_npc`/`to_npc`/`subject`/`content` and a `model_validator` that rejects self-loops. Engine entry raises `KeyError` on unknown `to_npc`. No silent fallbacks per CLAUDE.md.

### ACs Met

| AC | Requirement | Implementation |
|----|-------------|----------------|
| 1 | Two-phase belief propagation | `_Snapshot` list build + apply loop in `propagate()` |
| 2 | Contradiction detection, Fact preservation, downgrade to rumor | `_has_contradicting_fact()` + Suspicion-only storage + Fact untouched |
| 3 | Credibility decay with `decay_per_hop`, clamped at zero, OTEL attrs | `max(0.0, cred_before - decay_per_hop)` + span emits both readings + `accepted` |
| 4 | Two-NPC chain, contradiction, downgrade, multi-hop | All 4 covered by failing-now-passing tests (`TestTwoPhasePropagation`, `TestContradictionDetection`, `TestCredibilityDecay`, `TestOtelObservability`) |
| 5 | SPAN_GOSSIP_PROPAGATION + SPAN_BELIEF_STATE_MUTATION + residual contradiction logged | Both spans emit per transmission; `contradicted` rides span attrs; rejected gossip still emits propagation span |

### Self-Review Judgment Checks

- [x] **Code wired to consumers:** `GossipEngine` exports via `__all__`, importable from `sidequest.game.gossip_engine`. Span constants registered in `FLAT_ONLY_SPANS` (routing-completeness test passes). No production caller yet — flagged in Delivery Findings as a follow-up gap (ADR-087 P2 RESTORE bundle).
- [x] **Project patterns:** Follows `belief_state.py`'s pydantic `BaseModel` + `model_config = {"extra": "forbid"}` + clamped-constructor (`BeliefSuspicion.make`) idioms. Uses `Span.open()` context manager per `scenario_state.py`'s pattern.
- [x] **All ACs met:** 5/5 ACs have direct test coverage that passes.
- [x] **Error handling:** Constructor `ValidationError` on empty/self-loop input; `KeyError` on unknown `to_npc`. No silent swallowing. Credibility clamped at zero.

**Handoff:** To TEA (The Caterpillar) for verify phase — simplify fan-out + quality-pass gate.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned with documented narrowings
**Mismatches Found:** 5 (all minor; 4 recommend A — Update spec, 1 recommends C — Clarify spec, 0 recommend B — Fix code)

The implementation is structurally sound and lands all five ACs. The mismatches below are all narrowings — Dev simplified or constrained loosely-phrased AC language. None of the simplifications break the load-bearing guarantees (two-phase isolation, lineage tracking, Fact preservation, OTEL coverage). Most should be absorbed into the spec rather than re-opened in the code.

### Mismatches

1. **Topic filter missing from Phase 1** (missing-in-code — behavioral, minor)
   - Spec: AC1 says "subject to credibility and topic filters"
   - Code: only credibility filtering; gossip flows on any subject the transmission carries.
   - Recommendation: **D — Defer.** Topic-aware filtering is a higher-layer concern (NPC personality / OCEAN — ADR-042 — or scenario seed config), not engine core. The engine is the mechanical scaffold; what topics propagate is governed upstream by the caller's choice of transmissions. Future per-NPC topic gating belongs in the per-turn invocation site (the still-dark `session.py:698` between-turn pipeline), not here. Out of scope for 50-7.

2. **"Dispute resolution" is the preserve-and-append pattern, not an explicit algorithm** (ambiguous-spec — behavioral, minor)
   - Spec: AC1 says "contradictions trigger dispute resolution"; AC2 enumerates "acceptance, retention, or belief downgrade to 'rumor' tier"
   - Code: contradiction → existing Fact preserved + contradicting gossip appended as low-confidence Suspicion. That IS the union of retention + downgrade-to-rumor outcomes.
   - Recommendation: **A — Update spec.** The "dispute resolution" mechanism is the preserve-and-append rule. Code aligns with AC2's enumerated outcomes; there is no separate algorithm to add.

3. **Contradiction anchored only on BeliefFact, not on any belief type** (different-behavior — behavioral, minor)
   - Spec: AC2 says "contradicts an existing belief" (could read as any variant)
   - Code: `_has_contradicting_fact` checks only `BeliefFact` records; suspicions and claims don't anchor contradictions.
   - Recommendation: **A — Update spec.** Dev's narrowing is the right call: rumor-vs-rumor "contradictions" would be noise. Only Facts (witnessed/certain knowledge) are firm enough to flag gossip against. This deviation is already logged under Dev (implementation) deviations.

4. **"Credibility of source vs. existing belief holder is weighed" → Facts always win** (different-behavior — behavioral, minor)
   - Spec: AC2 says "Credibility of source vs. existing belief holder is weighed"
   - Code: Facts are immutable regardless of incoming credibility; gossip appends rumor, never overwrites.
   - Recommendation: **A — Update spec.** The weighing collapses to a single rule: "Facts win unconditionally." This is consistent with the rumor-tier-only storage policy and avoids the failure mode where a high-credibility gossiper could overwrite a witnessed fact. Document the rule explicitly in ADR-053's gossip section when it's revised.

5. **"Source credibility (NPC reputation, prior accuracy)"** (ambiguous-spec — architectural, minor)
   - Spec: AC3 says "Source credibility (NPC reputation, prior accuracy) factors into propagation decisions"
   - Code: "Source credibility" = `receiver.credibility_of(from_npc).score` (per-NPC trust map from `BeliefState.credibility_scores`). "Prior accuracy" — no track record of past-gossip-vs-eventual-truth is maintained.
   - Recommendation: **C — Clarify spec.** Define "source credibility" in this engine as receiver trust in source. "Prior accuracy" (track record across past gossip) is a future state-tracking enhancement requiring new fields on `BeliefState` (e.g. `gossip_track_record: dict[str, list[bool]]`). Out of scope for 50-7; would be a separate story.

### Architecture-level observations (not mismatches — flags for Reviewer)

- **SPAN_BELIEF_STATE_MUTATION nests inside SPAN_GOSSIP_PROPAGATION.** Consistent with parent-child observability hierarchy elsewhere in the codebase (e.g. encounter beats nesting inside turn spans). Good shape.
- **Double-signal on belief addition.** `receiver.add_belief()` emits `belief_state.belief_added` as an OTEL event on the current span. Inside the engine, "current span" is `SPAN_BELIEF_STATE_MUTATION`, so the event lands there. Net result: one mutation produces both a dedicated span AND an event — redundancy-by-design. Backward-compatible with existing belief_state event consumers; the dedicated span gives the GM panel a cleaner anchor.
- **`contradiction_threshold` constructor arg deliberately dropped.** TEA's contract used `...` as placeholder; no test demanded it; Dev correctly applied minimalist discipline. Future story can add it if a tuning need emerges.
- **Suspicion-only storage forward-compatible with 50-8.** Story 50-8 (AccusationEvaluator) consumes belief states. The `BeliefSourceToldBy(by=...)` discriminator on the Suspicion's `source` field carries the "told by" distinction that AccusationEvaluator will need to differentiate first-hand evidence from heard rumor.
- **No production caller.** Confirmed by both TEA and Dev. ADR-087's P2 RESTORE bundle covers this. Reviewer should NOT mark this as a blocker — story scope ends at the engine.

**Decision:** Proceed to verify.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (5235 / 5235 server tests passing; pyright clean on `gossip_engine.py`; lint clean on all 50-7-modified files)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3 (`sidequest/game/gossip_engine.py`, `sidequest/telemetry/spans/scenario.py`, `tests/game/test_gossip_engine.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 5 findings (2 high, 1 medium, 2 low/correct) | otel_capture fixture duplicates `tests/game/conftest.py:182` (which carries the Story 45-36 processor-clearing fix); `_events_named`/`_spans_named` helpers replicate a 7+ file pattern; `_sender_confidence` may want public promotion to `BeliefState`; `_has_contradicting_fact` low; span registration follows convention correctly. |
| simplify-quality | 4 findings (1 high, 1 medium, 2 low) | scenario.py missing `__all__` (codebase convention is actually inconsistent — only 1 span submodule uses it); SPAN_BELIEF_STATE_MUTATION emits both `npc` and `target_npc` (tests accept either, ambiguity is documented); intentional RED-imports flagged (acceptable); minor docstring terminology. |
| simplify-efficiency | 4 findings (1 high, 2 medium, 1 low) | `_Snapshot` pydantic→dataclass (applied); `_sender_confidence` intermediate list cosmetic; TransmissionOutcome field duplication; GossipResult wrap low. |

### Applied (2 high-confidence fixes)

1. **Remove duplicate `otel_capture` fixture** (simplify-reuse, high) — local fixture in `tests/game/test_gossip_engine.py` was a worse copy of the one in `tests/game/conftest.py:182`. The conftest version carries the Story 45-36 processor-clearing fix (`provider._active_span_processor._span_processors = ()`) that prevents span bleed-through between tests. Switching to the shared fixture removes 17 lines of duplication AND eliminates a latent test-isolation bug. Net delta: -28 lines in test file.
2. **Convert `_Snapshot` from pydantic `BaseModel` to frozen+slots `dataclass`** (simplify-efficiency, high) — `_Snapshot` is purely internal to `propagate()`, constructed and consumed within the same method, with values computed deterministically from already-validated inputs. Pydantic overhead added weight without safety benefit. Frozen dataclass with `slots=True` is the right primitive. Net delta: +3 LOC (clearer docstring), but removes a pydantic dependency from a hot path.

Regression after simplify: `pf check` — lint clean on all 50-7-touched files, pyright clean, 5235/5235 tests passing.

### Flagged for Reviewer (2 medium-confidence findings)

| # | Finding | Why flagged not applied |
|---|---------|-------------------------|
| 1 | Extract `_events_named` / `_spans_named` to `tests/_helpers/otel.py` | 7+ file refactor reaches outside story scope; bounded boy-scouting doesn't go exponential, but this one does. |
| 2 | Promote `_sender_confidence` to `BeliefState.max_confidence(subject)` public method | Would benefit 50-8 (AccusationEvaluator) and possibly narrator-context code, but defining a public API on `BeliefState` deserves a deliberate decision rather than a verify-phase auto-edit. |

### Noted (5 low-confidence observations)

| # | Finding | Disposition |
|---|---------|-------------|
| 1 | `scenario.py` missing `__all__` | Convention is inconsistent across the spans/ package — only `region_state.py` uses it; pre-change `scenario.py` also lacked it. Not a behavior issue. |
| 2 | SPAN_BELIEF_STATE_MUTATION carries both `npc` and `target_npc` attrs | Tests accept either; ambiguity is documented in the engine. Cosmetic. |
| 3 | `_has_contradicting_fact` could promote to `BeliefState.has_fact_about` | Defer until pattern recurs. |
| 4 | `GossipResult` wraps a single list | A pydantic single-list wrapper IS the codebase pattern for return values; matches `BeliefState`'s style. Leave. |
| 5 | `TransmissionOutcome` field duplication with `GossipTransmission` | Refactor would force downstream consumer changes in 50-8; minor maintenance cost is acceptable. |

### Reverted

None.

**Overall:** simplify: applied 2 high-confidence fixes; flagged 2 medium for Reviewer; noted 5 low.

**Quality Checks:** All passing — lint clean on diff, pyright clean, 5235/5235 tests green.

**Handoff:** To Reviewer (The Queen of Hearts) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 2 (format dirty + one suspected ordering flake) | confirmed 1 (format), reattributed 1 (flake is pre-existing on develop, not branch-introduced — see below) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 12 (5 high, 4 medium, 3 low) | confirmed 8, downgraded 3 (test quality gaps are non-blocking improvements), deferred 1 (wiring test scope — engine-level wiring covered by ADR-087 P2 follow-up per Architect line 327) |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 (1 high, 1 high, 1 medium) | confirmed 3 (docstring overstatement, stale RED disclaimer, test docstring AC mislabel) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 5 (3 high, 1 medium, 1 high) | confirmed 4 (silent fallback line 159, tautological assert line 314, bare truthy assert line 788, scenario.py __all__ — systemic, downgraded), 1 deferred (no production caller — explicit Architect ruling at session line 327 that this is not a blocker for 50-7 scope) |

**All received:** Yes (4 ran, 5 skipped per `workflow.reviewer_subagents` toggles — preflight, test_analyzer, comment_analyzer, rule_checker enabled; edge_hunter, silent_failure_hunter, type_design, security, simplifier disabled)
**Total findings:** 13 confirmed, 1 dismissed (preflight flake misattribution — see Pre-existing flake note below), 1 deferred (no production caller — Architect ruling)

### Pre-existing flake note

Preflight reported `tests/server/test_chargen_dispatch.py::TestSliceAWiring::test_caverns_delver_loadout_wired_into_snapshot` as an ordering-dependent flake triggered by the gossip test file. **Independently verified the chargen test is flaky in isolation on this branch (~13% failure rate over 15 isolated runs, 2/15 failed) without any gossip code being loaded.** My branch's 3 files (`gossip_engine.py`, `scenario.py`, `test_gossip_engine.py`) do not touch `random` module state, do not monkeypatch stdlib, and are not imported by `test_chargen_dispatch.py`. The chargen test inventory failure (duplicate items, missing `rations_day`) is consistent with a random-state issue that predates this branch. Reattributed as **pre-existing flake** and logged as a non-blocking Delivery Finding; it is not blocking this story.

## Rule Compliance

### CLAUDE.md "No Silent Fallbacks" (project rule, load-bearing)

| Type/Function/Field | Code Location | Compliant? | Evidence |
|---|---|---|---|
| `GossipTransmission.__init__` (pydantic validator) | gossip_engine.py:66-78 | YES | `Field(min_length=1)` on all 4 string fields; `@model_validator` rejects self-loops with explicit `ValueError`. Constructor refuses all silent fallbacks. |
| `GossipEngine.propagate` unknown `to_npc` | gossip_engine.py:153-157 | YES | Explicit `KeyError` with helpful message including the sorted keys of `npcs`. No silent fallback. |
| `GossipEngine.propagate` unknown `from_npc` | gossip_engine.py:159-166 | **NO** | `sender = npcs.get(t.from_npc)` then `if sender is not None:` silently falls through with `cred_before = trust` only. Asymmetric to `to_npc`. No log, no span attribute flag, no test. **Violation.** |
| `BeliefSuspicion.make` credibility clamp | gossip_engine.py:213 → belief_state.py:127 | YES | Clamping at construction is explicit, documented, and not a silent fallback (it's a documented invariant). |
| Span emission on rejected gossip | gossip_engine.py:185-198 | YES | Rejection path still emits `SPAN_GOSSIP_PROPAGATION` with `accepted=False` and `contradicted=True`. Tested by `test_rejected_gossip_still_emits_span` and `test_contradiction_outcome_is_visible_not_silently_dropped`. Compliant. |
| Contradiction outcome surfacing | gossip_engine.py:223-234 + 187-197 | YES | `contradicted` rides outcome AND span attrs; not dropped. Test coverage adequate. |

### CLAUDE.md "Verify Wiring, Not Just Existence" / "Every Test Suite Needs a Wiring Test"

| Component | Wiring Test Present? | Connected to Production? |
|---|---|---|
| `GossipEngine` exported from module | YES (test_gossip_engine_exported_from_module) | NO (no `session.py` / between-turn pipeline caller) |
| `SPAN_GOSSIP_PROPAGATION` registered | YES (test_gossip_span_constants_registered) | YES (in `FLAT_ONLY_SPANS`) |
| `SPAN_BELIEF_STATE_MUTATION` registered | YES (test_gossip_span_constants_registered) | YES (in `FLAT_ONLY_SPANS`) |

The "no production caller" finding is a **deferred** non-blocker per the Architect's explicit ruling at session line 327: "ADR-087's P2 RESTORE bundle covers this. Reviewer should NOT mark this as a blocker — story scope ends at the engine." TEA and Dev both logged it as a Delivery Finding follow-up. Honoring the upstream design decision; I am not overriding it.

### CLAUDE.md "No Stubbing"

| Module | Has stub/skeleton? |
|---|---|
| `sidequest/game/gossip_engine.py` | NO — every method is fully implemented; no `pass` placeholders, no `raise NotImplementedError` |
| `sidequest/telemetry/spans/scenario.py` | NO — constants are real, registered |
| `tests/game/test_gossip_engine.py` | NO — every test asserts real behavior |

### Python lang-review checks (delegated to reviewer-rule-checker; results cross-referenced)

| Rule | Status | Violations |
|------|--------|------------|
| #1 silent exceptions | clean | 0 |
| #2 mutable defaults | clean | 0 |
| #3 type annotations | clean | 0 |
| #4 logging | N/A (no logger import) | 0 |
| #5 path handling | N/A (no I/O) | 0 |
| #6 test quality | **VIOLATIONS** | 2 (line 314 tautological; line 788 bare truthy) |
| #7 resource leaks | clean | 0 (Span.open used as context manager) |
| #8 unsafe deserialization | N/A | 0 |
| #9 async pitfalls | N/A | 0 |
| #10 import hygiene | **VIOLATION** | 1 (scenario.py missing `__all__` — systemic, pre-existing pattern, downgraded) |
| #11 input validation | clean | 0 (pydantic boundary + KeyError) |
| #12 dependency hygiene | N/A | 0 (no dep changes) |
| #13 fix regressions | N/A | 0 (new module) |
| #14 cleanup ordering | clean | 0 (Span.open is not a one-shot lifecycle queue) |

## Devil's Advocate

I will argue this code is broken.

A malicious or careless caller constructs a transmission whose `from_npc` references an NPC the session does not know about — perhaps a stale name from an old save, a typo, an off-scene NPC the receiver has heard rumors about secondhand. The engine silently accepts this. `npcs.get(t.from_npc)` returns `None`. The engine then computes `cred_before = receiver.credibility_of(t.from_npc).score`, which defaults to **0.5 for any unknown NPC** (see belief_state.py:225-228). The gossip propagates with default credibility. No log, no span attribute, no error — the GM panel cannot tell whether this gossip came from a registered NPC at trust 0.5, or from a typo-generated phantom whose trust is unknowable. CLAUDE.md's "GM panel is the lie detector" principle says every subsystem decision must be observable. This one isn't.

A confused caller relies on the module docstring, which states: "contradicting gossip is flagged on the outcome and stored alongside the fact as low-confidence rumor." Reading this, they expect every contradicting transmission to land in the receiver's belief state. The actual code stores only when `credibility_after > 0.0`. A contradicting transmission from a zero-trust source produces `accepted=False`, `contradicted=True`, and **no belief state mutation** — the rumor is dropped, contradiction logged but the side effect the docstring promises never happens. The narrator code reading the docstring will malfunction.

A stressed filesystem produces no novel failure here (no I/O). But a stressed scenario — a tea_and_murder session with 20 NPCs and 50 gossip transmissions per turn — exercises the snapshot semantic. The test `test_snapshot_isolates_credibility_within_batch` claims to verify this but actually tests a scenario where `add_belief()` doesn't affect `credibility_scores`, so the snapshot guarantee is trivially satisfied regardless of implementation. A future refactor that interleaves phases would pass all tests and break the AC1 invariant silently.

A pessimistic reading: the engine's central guarantee (two-phase isolation) is under-tested; its central failure mode (unknown sender, undocumented behavior) is silently absorbed; its central side effect (belief state mutation) is conditioned on credibility but documented as unconditional. The combination is brittle. The 21 tests are GREEN, but greenness here measures the engine's claims about itself, not the claims it advertises to callers.

Conclusion: this code is shippable as an engine, not as an interface. The asymmetry between `to_npc` raising and `from_npc` silently absorbing is the load-bearing concern — fix it (raise consistently) or document it explicitly (with a passing test that proves the design is intentional).

## Reviewer Assessment

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] [RULE] | `tests/game/test_gossip_engine.py` is ruff-format dirty (would-reformat). Preflight blocker. | `tests/game/test_gossip_engine.py` (whole file) | `cd sidequest-server && uv run ruff format tests/game/test_gossip_engine.py` |
| [HIGH] [RULE] | Silent fallback: unknown `from_npc` in `npcs` dict is silently accepted; `cred_before` defaults to receiver-trust (0.5 for unknown senders). Asymmetric to `to_npc` which raises `KeyError`. No test, no docstring, no span attribute. Violates CLAUDE.md "No Silent Fallbacks". Engine claims this principle elsewhere in its own docstring (gossip_engine.py:60-61) but does not honor it here. | `sidequest/game/gossip_engine.py:159-166` | Decide: (a) raise `KeyError` for unknown `from_npc` symmetric to `to_npc`, and add a test asserting the raise; OR (b) document the design in the propagate docstring AND emit a span attribute (e.g., `sender_unknown: true`) on the propagation span AND add a test asserting the fallback semantic. Either is fine; silent acceptance is not. |
| [HIGH] [DOC] | Module docstring at gossip_engine.py:14-16 claims contradicting gossip is "stored alongside the fact as low-confidence rumor" — implies unconditional storage. Actual code stores only when `credibility_after > 0.0` (line 199). Contradicting gossip from a zero-trust source is flagged on the outcome but not stored. Misleads any caller relying on the docstring contract. | `sidequest/game/gossip_engine.py:14-16` | Reword to "contradicting gossip is flagged on the outcome and, when post-decay credibility remains positive, stored alongside the fact as a low-confidence `BeliefSuspicion`; zero-credibility contradictions are flagged but not stored." |
| [MEDIUM] [TEST] | `assert mutation_spans` is a bare truthy assertion (rule #6). Passes for any non-empty list regardless of count or content. Adjacent test correctly uses `assert len(spans) == 1`. | `tests/game/test_gossip_engine.py:443` | Replace with `assert len(mutation_spans) == 1` and pin expected attribute values (`attrs['npc'] == 'Bert'`, `attrs['confidence'] == pytest.approx(...)`). |
| [MEDIUM] [TEST] | No test asserts `SPAN_BELIEF_STATE_MUTATION` is NOT emitted when gossip is rejected (`credibility_after == 0.0`). The non-mutation path is untested; a regression that always emits the mutation span would pass current tests. | `tests/game/test_gossip_engine.py` (in `test_rejected_gossip_still_emits_span` near line 497) | Add: `assert len(_spans_named(otel_capture, SPAN_BELIEF_STATE_MUTATION)) == 0` to verify the rejection path doesn't emit the mutation span. |
| [MEDIUM] [TEST] | Multi-hop test uses weak inequality (`credibility_after < 0.7`) when the lineage math produces a deterministic 0.5. A refactor that returns 0.69 due to a rounding bug passes. | `tests/game/test_gossip_engine.py:361` | Tighten to `pytest.approx(0.5)` and add an assertion that `bert.beliefs_about("Erskine")` holds a Suspicion with confidence approx 0.7 after the first hop. |
| [MEDIUM] [DOC] | Test module docstring claims "the module under test does not yet exist; every test in this file fails at import time" — stale RED-phase disclaimer; both engine and tests ship in this diff. | `tests/game/test_gossip_engine.py:1-9` | Update docstring to describe the merged-state behavior. |
| [LOW] [TEST] | Tautological assertion: `assert result.outcomes[0].credibility_after >= 0.0` follows an equality assertion to `pytest.approx(0.0)` on the prior line. Rule #6: structurally adds zero coverage. | `tests/game/test_gossip_engine.py:314` | Remove the redundant `>= 0.0` line, or replace with a stronger property check (e.g., `outcome.credibility_after == max(0.0, outcome.credibility_before - 0.5)`). |
| [LOW] [DOC] | Test docstring labels `test_two_npc_chain_mutates_receiver_only` as "AC4"; the test actually exercises AC1 (two-phase propagation). AC4 covers multi-hop / downgrade scenarios elsewhere in the file. | `tests/game/test_gossip_engine.py:95` | Change docstring AC label to "AC1". |

### VERIFIED items (with rule-compatibility check)

- `[VERIFIED] [SEC] [SIMPLE]` Constructor-time validation on `GossipTransmission` is exhaustive and consistent — gossip_engine.py:66-78 sets `Field(min_length=1)` on all four string fields, model_validator rejects self-loops with explicit error. Rule compliance: CLAUDE.md "No Silent Fallbacks" — compliant at construction. Test coverage: `TestInputValidation` (5 tests).
- `[VERIFIED] [TYPE]` Pydantic models use `model_config = {"extra": "forbid"}` consistently on `GossipTransmission`, `TransmissionOutcome`, `GossipResult` — gossip_engine.py:64, 88, 103. Matches the codebase pattern (e.g. belief_state.py:108, 139, 184). No extra-field smuggling.
- `[VERIFIED] [TYPE]` `_Snapshot` was correctly demoted from pydantic to frozen `dataclass(slots=True)` per simplify-efficiency — gossip_engine.py:244-258. Internal-only type, computed deterministically from validated inputs. No type invariant lost.
- `[VERIFIED] [EDGE]` Credibility clamp at zero — gossip_engine.py:168 `max(0.0, cred_before - self.decay_per_hop)`. Boundary tested by `test_decay_clamps_at_zero`.
- `[VERIFIED] [EDGE]` Sender immutability — `propagate()` never mutates `npcs[t.from_npc].beliefs`. Verified by reading the loop body (no `sender.add_belief()` call anywhere). Tested by `test_two_npc_chain_mutates_receiver_only`.
- `[VERIFIED] [SILENT]` Rejected-gossip path still emits `SPAN_GOSSIP_PROPAGATION` with `accepted=False` — gossip_engine.py:185-198, condition is on `credibility_after > 0.0` for mutation, but the propagation span fires unconditionally. Tested by `test_rejected_gossip_still_emits_span`. No silent drop on rejection.
- `[VERIFIED] [TYPE]` Existing `BeliefFact` records are never overwritten — gossip_engine.py only calls `receiver.add_belief()` which appends, never replaces. Verified by reading belief_state.py:199-213 (no removal path). Tested by `test_contradicting_gossip_against_existing_fact_is_flagged` asserting `len(facts) == 1` after the call.

### Challenge: my VERIFIEDs against subagent findings

- I marked `[SILENT]` rejected-gossip emits span as VERIFIED. Test-analyzer flagged "no test that SPAN_BELIEF_STATE_MUTATION is NOT emitted on rejection." Both are correct — propagation span emits unconditionally (VERIFIED), but the non-mutation-span assertion is missing (flagged). Both findings stand and do not contradict.
- I marked `[EDGE]` credibility clamp as VERIFIED via `test_decay_clamps_at_zero`. Rule-checker flagged the next-line tautological assertion in the same test (line 314 `>= 0.0` redundant). The clamp is verified; the redundant assertion is a separate test-quality finding.
- I marked `[SEC]` constructor validation as VERIFIED. Rule-checker confirms input validation is clean (rule #11). No contradiction.

### Findings by subagent tag (per gate requirement)

- `[EDGE]` (edge-hunter — disabled via settings; my own analysis flagged: missing pre-existing-Fact+Suspicion-on-same-subject test case — non-blocking improvement)
- `[SILENT]` (silent-failure-hunter — disabled via settings; rule-checker caught the silent fallback at gossip_engine.py:159 — confirmed HIGH)
- `[TEST]` (test-analyzer — bare truthy assert at line 443 [MEDIUM], weak multi-hop inequality at line 361 [MEDIUM], tautological assert at line 314 [LOW], missing rejection-no-mutation-span assertion [MEDIUM])
- `[DOC]` (comment-analyzer — module docstring overstatement on contradiction storage [HIGH], stale RED disclaimer [MEDIUM], test docstring AC mislabel [LOW])
- `[TYPE]` (type-design — disabled via settings; my own analysis: pydantic models well-formed, `_Snapshot` correctly demoted, no findings)
- `[SEC]` (security — disabled via settings; my own analysis: constructor input validation is exhaustive, no SQL/HTML/path traversal surface in this diff, no findings)
- `[SIMPLE]` (simplifier — disabled via settings; TEA's simplify-pass already applied 2 high-confidence fixes during verify; no new findings)
- `[RULE]` (rule-checker — silent fallback at line 159 [HIGH], tautological assert at line 314 [LOW], bare truthy assert at line 443/788 [MEDIUM], scenario.py missing `__all__` [LOW — systemic], no production caller [DEFERRED per Architect ruling])

**Blocking Findings:** 3 (1 mechanical [HIGH format dirty], 1 logic/test [HIGH silent fallback], 1 documentation [HIGH lying docstring])

**Handoff:** Back to TEA (The Caterpillar) for red rework — the silent-fallback decision needs a failing test that pins the chosen design, the lying docstring needs to be updated, and the test-quality fixes need test-side work. Format fix is mechanical and rides along.

## TEA Assessment (red rework — round-trip 1)

**Phase:** finish (rework)
**Status:** RED — 1 failing test, 23 passing on `tests/game/test_gossip_engine.py` (clean RED: exactly the silent-fallback test fails, every tightening locks current-correct behavior)

### Design decision: unknown `from_npc` MUST raise `KeyError`

Reviewer offered two paths for the load-bearing silent-fallback finding (option A: raise; option B: document the fallback + emit a span attr + add a test asserting the fallback). I picked **option A** — raise — for these reasons:

1. **Consistency with `to_npc`.** The engine already raises `KeyError` at `gossip_engine.py:153-157` when `to_npc` is missing. Symmetric handling of unknown participants is the principle of least surprise; the asymmetric current state is the surprise.
2. **CLAUDE.md "No Silent Fallbacks" is binding.** The rule is explicit, and the engine's own docstring at `gossip_engine.py:60-61` self-cites it. Honoring the rule the engine claims to follow is cheaper than introducing a documented exception.
3. **Off-scene-sender is not a current requirement.** No AC, no Architect spec-check note, no Dev Improvement asks for "gossip from an NPC the session doesn't know about." If that becomes a real game scenario later, it should be an explicit opt-in (e.g. `transmission.allow_off_scene_sender: bool = False`) rather than a silent default.
4. **Caller-bug surfacing.** A typo or stale name in `from_npc` should fail loudly at the engine boundary. The default 0.5 credibility-for-strangers from `BeliefState.credibility_of` is a meaningful semantic for *known* strangers, not a fallback for *missing* NPCs.

### Test changes

**Tests modified or added in `tests/game/test_gossip_engine.py`:**

| Change | Test | Severity addressed | New status |
|--------|------|--------------------|------------|
| **NEW** | `test_propagate_rejects_unknown_from_npc` | Reviewer HIGH (silent fallback @ gossip_engine.py:159) + rule-checker rule 15 | **RED** — the only failing test; pins option-A design decision |
| **NEW** | `test_contradicting_gossip_with_zero_credibility_is_not_stored` | Reviewer HIGH (lying docstring on contradiction storage) | GREEN — engine already enforces the conditional storage; this test locks it so the docstring fix can't drift back |
| **NEW** | `test_mutation_span_nested_inside_propagation_span` | Reviewer MEDIUM (missing parent-span assertion) | GREEN — asserts `mutation_spans[0].parent.span_id == propagation_spans[0].context.span_id` |
| Tightened | `test_contradicting_gossip_against_existing_fact_is_flagged` | Pin Suspicion-storage path when cred>0 | GREEN — added BeliefSuspicion existence + confidence assertions |
| Tightened | `test_multi_hop_decays_more_than_single_hop` | Reviewer MEDIUM (weak inequality) | GREEN — `< 0.7` → `pytest.approx(0.5)`; also asserts Bert's stored Suspicion confidence = 0.7 after turn 1 |
| Tightened | `test_propagate_emits_gossip_span_per_transmission` | Reviewer MEDIUM (`'X' in attrs` vacuous presence) | GREEN — every attribute pinned to exact expected value (credibility_before=0.6, credibility_after=0.5, accepted=True, etc.) |
| Tightened | `test_belief_state_mutation_span_fires_when_receiver_updates` | Reviewer MEDIUM (bare `assert mutation_spans`) + rule-checker rule #6 | GREEN — `len(mutation_spans) == 1`, `attrs["npc"] == "Bert"`, `attrs["confidence"] == pytest.approx(0.8)`; dropped the `npc or target_npc` ambiguity in favor of canonical `npc` key |
| Renamed | `test_rejected_gossip_still_emits_span` → `test_rejected_gossip_still_emits_span_but_no_mutation` | Reviewer MEDIUM (no test for rejection→no-mutation-span) | GREEN — asserts mutation_spans == [] and Bert's belief_state untouched on rejection |
| Tightened | `test_propagate_rejects_unknown_to_npc` | Test-analyzer MEDIUM (permissive `(KeyError, ValueError)` union) | GREEN — narrowed to `pytest.raises(KeyError)` per documented contract |
| Removed | tautological `>= 0.0` after equality `approx(0.0)` (line 314) | Reviewer LOW + rule-checker rule #6 | n/a — line deleted |
| Fixed docstring | module docstring (lines 1-9) | Reviewer LOW (stale RED disclaimer) | n/a — replaced with merged-state description |
| Fixed docstring | `test_two_npc_chain_mutates_receiver_only` (line 84) | Reviewer LOW (mislabeled AC4) | n/a — relabeled AC1 |
| Removed | unused `_events_named` helper | Reviewer non-blocking gap (dead code) | n/a — function deleted |

**Format:** `tests/game/test_gossip_engine.py` was reformatted with `uv run ruff format`. Verified clean. This closes Reviewer's HIGH format-dirty finding directly (test file is TEA's domain).

### What Dev still needs to do in GREEN

1. **Add the `from_npc` existence check in `propagate()`** — symmetric to the existing `to_npc` check at gossip_engine.py:153-157. Raise `KeyError` with a helpful message including the sorted keys of `npcs`. This turns the RED test green.

2. **Fix the lying module docstring** at `sidequest/game/gossip_engine.py:14-16`. Current text: "contradicting gossip is flagged on the outcome and stored alongside the fact as low-confidence rumor." Replace with: "contradicting gossip is flagged on the outcome and, when post-decay credibility remains positive, stored alongside the fact as a low-confidence `BeliefSuspicion`; zero-credibility contradictions are flagged but not stored." The `test_contradicting_gossip_with_zero_credibility_is_not_stored` test locks the conditional-storage contract going forward.

3. **No other code changes needed.** The engine's existing behavior on all other tightenings matches the new strict assertions — Dev's GREEN is narrowly scoped to (1) the from_npc raise and (2) the docstring fix.

### Rule Coverage (Python lang-review, this rework)

| Rule | New/Modified Tests | Status |
|------|---------------------|--------|
| #1 silent exceptions / fallbacks | `test_propagate_rejects_unknown_from_npc` — pins KeyError raise | RED (drives Dev fix) |
| #6 test quality (no vacuous assertions) | All tightenings — eliminated `assert mutation_spans`, redundant `>= 0.0`, `'X' in attrs` placeholders, `(KeyError, ValueError)` permissive union | GREEN (audit clean) |
| #11 input validation at boundaries | `test_propagate_rejects_unknown_from_npc`, `test_propagate_rejects_unknown_to_npc` | RED + GREEN (boundary symmetry) |

**Self-check:** Re-audited every assertion in the modified file. Zero vacuous assertions remaining. Every `assert` either pins an exact value, an exact count, an exact exception type, or an exact span parent relation. No `let _ =` analogue, no truthy-only checks on attributes the GM panel reads.

### Quality Checks

| Check | Status |
|-------|--------|
| `uv run pytest tests/game/test_gossip_engine.py` | 1 failed (intentional RED), 23 passed |
| `uv run ruff check tests/game/test_gossip_engine.py` | All checks passed |
| `uv run ruff format --check tests/game/test_gossip_engine.py` | 1 file already formatted |

**Handoff:** To Dev (The White Rabbit) for GREEN.

## Dev Assessment (green rework — round-trip 1)

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/game/gossip_engine.py` — 18 insertions, 9 deletions

### Changes

**1. `from_npc` existence check at engine entry** (resolves Reviewer HIGH silent-fallback + TEA RED test):

```python
if t.from_npc not in npcs:
    raise KeyError(
        f"GossipTransmission names unknown from_npc {t.from_npc!r} "
        f"(not in npcs map: {sorted(npcs)})"
    )
```

Placed immediately after the existing `to_npc` check, mirroring the pattern. Message format and `sorted(npcs)` debugging hint match the `to_npc` raise verbatim — the two raises are now structurally identical, the symmetry the Reviewer/TEA decision asked for.

**2. Dropped dead silent-fallback guard.** With the existence check above, `sender = npcs[t.from_npc]` is total (no `None` case). Removed the `if sender is not None:` indent because the `None` branch can no longer execute. CLAUDE.md "No Stubbing" + minimalist discipline: don't keep code that can't run.

**3. Module docstring corrected on conditional contradiction storage** (resolves Reviewer HIGH lying-docstring):

Before: "contradicting gossip is flagged on the outcome and stored alongside the fact as low-confidence rumor."

After: "contradicting gossip is flagged on the outcome and, when post-decay credibility remains positive, stored alongside the fact as a low-confidence `BeliefSuspicion`. Zero-credibility contradictions are flagged on the outcome but not stored — the receiver's trust in the source has fully decayed, so no rumor lands."

The TEA-added `test_contradicting_gossip_with_zero_credibility_is_not_stored` locks this contract in place going forward.

**4. `Raises:` section updated** to document the new `from_npc` KeyError path alongside the existing `to_npc` one.

### Test Results

| Check | Status |
|-------|--------|
| `uv run pytest tests/game/test_gossip_engine.py` | **24/24 passing** (was 23/24 RED + 1 expected fail; now all green) |
| `uv run pytest` (full server suite) | **5238 passed, 0 failed, 64 skipped** in 103s (up from 5235 because TEA added 3 new tests in rework) |
| `uv run ruff check sidequest/game/gossip_engine.py` | All checks passed |
| `uv run ruff format --check sidequest/game/gossip_engine.py` | already formatted |
| `uv run pyright sidequest/game/gossip_engine.py` | 0 errors, 0 warnings, 0 informations |

### What Did NOT Change

Per minimalist discipline, scope held to exactly what TEA's tests demanded:
- No other docstring rewrites (the load-bearing one was the contradiction-storage paragraph)
- No refactor of `_sender_confidence`, `_has_contradicting_fact`, `_Snapshot`, or the propagate loop
- No public-API additions (no `BeliefState.max_confidence` promotion — that's a 50-8 question)
- No new span attributes (no `sender_unknown: true` because option A — raise — was chosen, not option B — document the fallback)
- No `__all__` added to `scenario.py` (Reviewer downgraded as systemic pre-existing pattern)
- No production caller added (Architect explicit ruling: out of scope, ADR-087 P2)

### Reviewer Findings Disposition

| # | Severity | Finding | Status |
|---|----------|---------|--------|
| 1 | HIGH | test_gossip_engine.py ruff-format dirty | **resolved by TEA in red rework** (test file is TEA's domain) |
| 2 | HIGH | Silent fallback on unknown `from_npc` | **resolved** — KeyError raise added, test green |
| 3 | HIGH | Module docstring overstates contradiction storage | **resolved** — docstring rewritten, contract locked by new test |
| 4 | MEDIUM | Bare truthy `assert mutation_spans` | **resolved by TEA in red rework** (test tightening) |
| 5 | MEDIUM | No "rejection emits no mutation span" assertion | **resolved by TEA in red rework** |
| 6 | MEDIUM | Multi-hop weak inequality | **resolved by TEA in red rework** (`< 0.7` → `approx(0.5)`) |
| 7 | MEDIUM | Stale RED disclaimer in test docstring | **resolved by TEA in red rework** |
| 8 | LOW | Tautological `>= 0.0` after `approx(0.0)` | **resolved by TEA in red rework** |
| 9 | LOW | test_two_npc_chain mislabeled AC4 | **resolved by TEA in red rework** |
| — | DEFERRED | scenario.py missing `__all__` | non-blocking, systemic |
| — | DEFERRED | No production caller | non-blocking per Architect ruling, ADR-087 P2 |
| — | NON-BLOCKING | Pre-existing chargen test flake | not introduced by 50-7 (logged in Delivery Findings) |

All 3 HIGH blockers resolved. All MEDIUM/LOW resolved. 2 DEFERRED items honor upstream rulings.

**Handoff:** To TEA (The Caterpillar) for verify phase — simplify fan-out + quality-pass on the small rework diff.

## Architect Assessment (spec-check — round-trip 1)

**Spec Alignment:** Aligned
**Mismatches Found:** None

### Rework Scope Audit

The round-trip 1 diff is narrowly scoped: 18 insertions / 9 deletions on `sidequest/game/gossip_engine.py` only. Two changes, both explicitly demanded by TEA's failing test and Reviewer's docstring finding:

1. **`from_npc` existence check** at `propagate()` entry, raising `KeyError` symmetric to the existing `to_npc` check. Eliminates the silent-fallback path the Reviewer flagged. The dead `if sender is not None:` branch was removed because, with the raise above, `sender` is now total. Net behavior: unknown participants on either side of a transmission raise; known participants behave identically to before. No AC speaks to off-scene-sender support, so the tightening is purely additive in the failure-mode direction — no behavior change for any well-formed caller.

2. **Module docstring at lines 14-16** rewritten to describe conditional contradiction storage (positive credibility → stored as Suspicion alongside Fact; zero credibility → flagged but not stored). The code's storage condition (`if snap.credibility_after > 0.0:`) is unchanged; only the docstring was wrong. The TEA-added `test_contradicting_gossip_with_zero_credibility_is_not_stored` locks the contract.

### AC Alignment Check (post-rework)

| AC | Status post-rework | Notes |
|----|---------------------|-------|
| AC1 — two-phase propagation | unchanged | snapshot/integrate loop intact |
| AC2 — contradiction detection, Fact preservation, downgrade to rumor | tightened | docstring now matches the conditional-storage code; no behavior change |
| AC3 — credibility decay + OTEL | unchanged | clamp at zero intact, spans unchanged |
| AC4 — integration tests | strengthened | multi-hop test now pins exact value (0.5); 2 new tests added by TEA |
| AC5 — OTEL observability + no silent drops | strengthened | parent-span nesting and no-mutation-on-rejection now explicitly asserted |

The new `from_npc` raise sits outside the AC enumeration — it's a defensive boundary check rather than an AC-mandated feature — but is consistent with the engine's self-cited adherence to CLAUDE.md "No Silent Fallbacks", which the original implementation claimed to follow but did not enforce on the `from_npc` axis.

### Mismatch Resolution Audit

Of the 5 mismatches I logged in the round-trip 0 spec-check, none are newly impacted by this rework:

| # | Original mismatch | Round-trip 1 status |
|---|---|---|
| 1 | Topic filter missing from Phase 1 | unchanged — still deferred per round-trip 0 recommendation D |
| 2 | "Dispute resolution" is preserve-and-append | unchanged — round-trip 1 docstring fix clarifies this further |
| 3 | Contradiction anchored only on BeliefFact | unchanged |
| 4 | "Credibility of source vs. existing belief holder weighed" → Facts always win | unchanged |
| 5 | "Prior accuracy" not maintained | unchanged |

The rework introduces **zero** new mismatches. The two changes are purely corrective: one closes a silent fallback (now consistent with the engine's stated principles), the other aligns a docstring with its code. Both are mismatches the Reviewer caught that I missed in round-trip 0.

### Self-Audit

In retrospect, the round-trip 0 spec-check should have caught both findings:

- The silent fallback on unknown `from_npc` was visible in the same `propagate()` body where I noted the `to_npc` raise. Asymmetric error handling on adjacent lines is exactly the kind of structural pattern a spec-check should flag. I missed it.
- The module docstring overstatement on contradiction storage was readable side-by-side with the code's storage gate. I read both but didn't cross-check.

Logging here so future spec-checks weight (a) asymmetric error handling within the same method body, and (b) docstring↔code paragraph alignment, higher when scanning small modules.

**Decision:** Proceed to verify. The rework cleanly closes the Reviewer's HIGH blockers without introducing new architectural concerns.

**Handoff:** To TEA (The Caterpillar) for verify phase — simplify fan-out + quality-pass on the small rework diff.

## TEA Assessment (verify — round-trip 1)

**Phase:** finish (rework)
**Status:** GREEN confirmed — 24/24 on `tests/game/test_gossip_engine.py`, 5238/5238 on the full server suite (264 passed across gossip + adjacent suites: `tests/game/test_belief_state.py`, `tests/game/test_scenario_state.py`, `tests/server/test_scenario_bind.py`, `tests/telemetry/`).

### Simplify Report

**Teammates:** reuse, quality, efficiency (all three on the round-trip 1 diff only — `HEAD~2..HEAD`)
**Files Analyzed:** 2 (`sidequest/game/gossip_engine.py`, `tests/game/test_gossip_engine.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | No extraction opportunities meeting the high-confidence threshold. The two KeyError raises (to_npc, from_npc) are structurally identical but only 2 sites; helper extraction would require 4-arg parameter boilerplate. `_spans_named` is correctly retained (7 call sites). New test scaffolding is pedagogical and intentionally inline. |
| simplify-quality | clean | Docstring matches code (storage condition `credibility_after > 0.0` accurately described). KeyError messages consistent and symmetric. New test names follow the established `test_<subject>_<condition>_<outcome>` convention. No dead code or orphaned references after removing the `if sender is not None:` guard. The combined name `test_rejected_gossip_still_emits_span_but_no_mutation` is appropriate — both halves describe the same rejection-observability invariant. |
| simplify-efficiency | clean | `from_npc` validation correctly placed inside the per-transmission loop (per-NPC, not hoistable). `sorted(npcs)` in error messages is acceptable on the error path with n≤20. The duplication between `test_belief_state_mutation_span_fires_when_receiver_updates` and `test_mutation_span_nested_inside_propagation_span` is intentional — they verify orthogonal properties (attributes vs. parent linkage) and the inline setup self-documents the scenario. No premature abstractions. |

### Applied

**None.** All three teammates returned `findings: []`. The rework diff is small, targeted, and clean — no high-confidence fixes to apply.

### Flagged for Reviewer

**None.** No medium-confidence findings.

### Noted

**None.** No low-confidence observations either.

### Reverted

**None.**

**Overall:** simplify: clean across all three lenses. The rework adds the `from_npc` raise and docstring fix that the Reviewer demanded, with no incidental drift, no dead code, no over-engineering. Test additions are minimal and orthogonal.

### Quality Checks

| Check | Status |
|-------|--------|
| `uv run pytest tests/game/test_gossip_engine.py` | 24/24 passing |
| `uv run pytest` (full server suite) | 5238 passed, 0 failed, 64 skipped |
| `uv run ruff check {3 modified files}` | All checks passed |
| `uv run ruff format --check {3 modified files}` | 3 files already formatted |
| `uv run pyright sidequest/game/gossip_engine.py` | 0 errors, 0 warnings, 0 informations |

**Handoff:** To Reviewer (The Queen of Hearts) for round-trip 2 code review.

## Subagent Results (round-trip 2)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — all 4 mechanical checks green (24/24 gossip tests, lint clean, format clean, pyright clean) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 2 new (1 LOW, 1 MEDIUM); all 6 round-trip 0 test findings confirmed fixed | confirmed 2 (inline imports LOW, misleading update_credibility setup MEDIUM); both non-blocking |
| 5 | reviewer-comment-analyzer | Yes | findings | 1 new (LOW); all 3 round-trip 0 doc findings confirmed fixed | confirmed 1 (method docstring at propagate Phase 2 doesn't cross-ref the contradiction sub-case the module docstring covers); non-blocking |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | TEA's verify-rework simplify fan-out already returned clean across all 3 lenses (reuse, quality, efficiency) |
| 9 | reviewer-rule-checker | Yes | findings | 2 new LOW (1 dup with test-analyzer); all 4 round-trip 0 rule violations confirmed fixed | confirmed 2 (`.get()` vs `attrs[key]` inconsistency on line 602, inline imports of span constants — same as test-analyzer's LOW); both non-blocking |

**All received:** Yes (4 ran, 5 skipped per `workflow.reviewer_subagents` toggles)
**Total findings:** 4 confirmed (1 MEDIUM, 3 LOW), 0 dismissed, 0 deferred. **Net: zero new blockers, all round-trip 0 blockers closed.**

### Round-trip 0 finding closure

| # | RT0 Severity | RT0 Finding | RT2 Status |
|---|----|---|---|
| 1 | HIGH | test_gossip_engine.py ruff-format dirty | FIXED (TEA red rework reformat) |
| 2 | HIGH | Silent fallback on unknown `from_npc` | FIXED (Dev added KeyError raise mirroring to_npc) |
| 3 | HIGH | Module docstring overstates contradiction storage | FIXED (Dev rewrote docstring with conditional-storage description) |
| 4 | MEDIUM | Bare truthy `assert mutation_spans` | FIXED (TEA replaced with `len == 1` + exact attr pins) |
| 5 | MEDIUM | No "rejection emits no mutation span" assertion | FIXED (TEA renamed test + added `mutation_spans == []` check) |
| 6 | MEDIUM | Multi-hop weak inequality `< 0.7` | FIXED (TEA `pytest.approx(0.5)` + stored-Suspicion confidence pin) |
| 7 | MEDIUM | Stale RED disclaimer in test module docstring | FIXED (TEA rewrote with merged-state description) |
| 8 | LOW | Tautological `>= 0.0` after `approx(0.0)` | FIXED (TEA line removed) |
| 9 | LOW | `test_two_npc_chain` mislabeled AC4 | FIXED (TEA relabeled AC1) |
| — | NON-BLOCKING | Unused `_events_named` helper | FIXED (TEA removed) |
| — | NON-BLOCKING | scenario.py missing `__all__` (systemic) | preserved (correctly not changed) |
| — | NON-BLOCKING | No production caller | preserved per Architect ruling (ADR-087 P2) |
| — | NON-BLOCKING | Pre-existing chargen test flake | unrelated to branch (round-trip 0 reattributed) |

All HIGH and MEDIUM closed. All LOW closed. Three NON-BLOCKING items honored as previously decided.

## Devil's Advocate (round-trip 2)

I argue this code is still broken.

The rework introduces a regression nobody noticed: the new `from_npc` raise is placed inside the per-transmission loop, so a batch of transmissions whose first entry is well-formed but third entry references an unknown sender will raise mid-loop *after* the first two transmissions have already updated their snapshots in the `snapshots` list. Wait — no. Snapshots are appended in Phase 1 only; Phase 2 mutations happen in the separate second loop. The KeyError fires during Phase 1, and Phase 2 never starts. No receiver belief state is touched. The two-phase discipline holds. False alarm.

I argue the misleading `bert.update_credibility("Alice", 0.5)` in `test_propagate_rejects_unknown_from_npc` is a teaching trap: a reader notices the credibility setup, assumes it matters, and may copy the pattern into a different test where the setup IS load-bearing — except their copy will silently work because the data flow happens to align. The trap is real but the cost is low (one test, one reader at a time). The fix (delete the line) is trivial and could ride along on any 50-8 follow-up that touches this file. Non-blocking.

I argue the inline imports of `SPAN_GOSSIP_PROPAGATION` and `SPAN_BELIEF_STATE_MUTATION` in five test methods are a latent breakage waiting to happen. If `sidequest.telemetry.spans.scenario` is ever renamed or refactored, the top-level imports break loudly while the inline imports break silently per-test. Same low-cost fix: hoist them to the top. Non-blocking.

I argue the `.get("contradicted") is True` pattern on line 602 is a leftover from before round-trip 0's tightening pass. The rest of the file now uses direct key access; this one site reads as deliberate ambiguity. A future regression that emits the span without the `contradicted` attribute would surface (`None is True` is False), but the diagnostic is poorer than a `KeyError` saying "where is 'contradicted'?". Cosmetic; not blocking.

A stressed runtime hits the new `from_npc` raise on every miscall. Good. A confused caller sees identical error messages for to_npc and from_npc failures, with the offending NPC name and the sorted set of valid NPCs. Good. A reader of the module docstring now learns the conditional-storage contract; a reader of only the method docstring still doesn't see the contradiction sub-case explicitly. Minor doc inconsistency, not a behavior bug.

A pessimistic reading: the rework is tight enough that the only remaining concerns are cosmetic. The HIGH and MEDIUM Round-trip 0 findings are dead. The new findings are all LOW (with one MEDIUM that the test-analyzer correctly flagged as misleading-but-harmless). The engine is now consistent with its own docstring's self-cited principles. The tests are tight, exact, and orthogonal where they need to be.

Conclusion: this code is shippable. The Queen's standards are demanding but not arbitrary — when the standards are met, approval follows.

## Reviewer Assessment (round-trip 2)

**Verdict:** APPROVED

**Data flow traced:** `GossipTransmission` (constructor-validated for non-empty strings + self-loop rejection) → `propagate()` entry (raises KeyError on unknown to_npc OR from_npc, symmetric) → Phase 1 snapshot loop (computes credibility + contradiction flags, no mutation) → Phase 2 integration loop (emits propagation span, optionally emits nested mutation span and appends Suspicion when `credibility_after > 0.0`). Sender immutability preserved; receiver Facts never overwritten; contradictions visible on outcome + span. Safe because every boundary is loud and every side effect is observable.

**Pattern observed:** Symmetric boundary checks for participants — `to_npc` and `from_npc` raises at `gossip_engine.py:153-167` are structurally identical. Matches CLAUDE.md "No Silent Fallbacks" and the engine's self-cited adherence to that principle. Good shape.

**Error handling:** Two raise sites for unknown NPCs at `gossip_engine.py:153-157` and `gossip_engine.py:159-163`. Constructor-level validation on `GossipTransmission` at `gossip_engine.py:64-78` (pydantic Field + model_validator). Credibility clamped at zero at `gossip_engine.py:171`. No silent paths.

**Non-blocking observations (would-fix if convenient, not requesting rework):**

| Severity | Tag | Issue | Location | Suggested fix |
|----------|-----|-------|----------|---------------|
| [MEDIUM] | [TEST] | `bert.update_credibility("Alice", 0.5)` in `test_propagate_rejects_unknown_from_npc` is unused — the engine raises before reading credibility. Misleading setup. | `tests/game/test_gossip_engine.py` (the new test added in red rework) | Delete the line, or replace with a comment noting the setup is intentionally minimal. |
| [LOW] | [TEST] [RULE] | Five test methods import `SPAN_GOSSIP_PROPAGATION` / `SPAN_BELIEF_STATE_MUTATION` inline inside their function bodies. `TestWiring` correctly hoists them. Inconsistency violates rule #10. | `tests/game/test_gossip_engine.py:438, 483, 523, 567, 616` | Hoist the imports to the top-level import block alongside the existing `gossip_engine` imports. |
| [LOW] | [RULE] | `attrs.get("contradicted") is True` on line 602 uses `.get()` while every other span-attr check now uses direct key access. Inconsistent. | `tests/game/test_gossip_engine.py:602` | Change to `attrs["contradicted"] is True` for consistency and clearer KeyError diagnostic. |
| [LOW] | [DOC] | `propagate()` Phase 2 docstring at gossip_engine.py:143-148 says "if credibility is positive, append a `BeliefSuspicion`" but doesn't explicitly note that the same gate covers the contradiction sub-case. The module docstring at lines 14-21 does cover it; method docstring lacks the cross-reference. | `sidequest/game/gossip_engine.py:143-148` | Append one clause: "this gate applies equally to contradicting gossip — positive credibility lands as Suspicion alongside the preserved Fact; zero credibility is flagged but not stored." |

These will be tracked as non-blocking Improvements in Delivery Findings; they are NOT blockers.

### VERIFIED items (with rule-compatibility check)

- `[VERIFIED] [SILENT] [RULE]` from_npc raise lands at `gossip_engine.py:159-163` with message format and `sorted(npcs)` suffix identical to the to_npc raise at lines 153-157. Symmetric handling. CLAUDE.md "No Silent Fallbacks" rule honored. Test `test_propagate_rejects_unknown_from_npc` covers the new raise (verified PASS at round-trip 1 green).
- `[VERIFIED] [DOC]` Module docstring rewrite at `gossip_engine.py:14-21` accurately describes the storage gate. Cross-referenced against the code at the storage gate (storage condition `credibility_after > 0.0`). Docstring and code now agree.
- `[VERIFIED] [TEST]` All 6 round-trip 0 test-quality findings closed. The `test_rejected_gossip_still_emits_span_but_no_mutation` test now exercises both halves of the rejection-observability invariant.
- `[VERIFIED] [SIMPLE]` Dead `if sender is not None:` guard removed; `sender = npcs[t.from_npc]` is total after the new existence check. No dead code introduced; one branch deleted.
- `[VERIFIED] [TYPE]` No type-design changes in the rework; pydantic models and `_Snapshot` dataclass unchanged. Round-trip 0 verifications stand.
- `[VERIFIED] [SEC]` Input validation surface unchanged (constructor validators intact) AND strengthened by the new from_npc boundary check. Tested by `TestInputValidation`.
- `[VERIFIED] [EDGE]` Boundary cases checked: zero-credibility-contradiction not-stored (new test), rejection-no-mutation-span (renamed/expanded test), multi-hop exact value pin (tightened test).

### Findings by subagent tag (all 8 must appear per gate)

- `[EDGE]` edge-hunter disabled via settings; my own analysis: rework strengthens boundary tests, no new edge cases needed
- `[SILENT]` silent-failure-hunter disabled via settings; rule-checker confirmed the from_npc raise closes the round-trip 0 silent fallback; no new silent paths
- `[TEST]` test-analyzer: 2 findings — `[MEDIUM]` misleading `update_credibility` setup, `[LOW]` inline imports of span constants
- `[DOC]` comment-analyzer: 1 finding — `[LOW]` method docstring at `propagate()` Phase 2 missing contradiction sub-case cross-reference
- `[TYPE]` type-design disabled via settings; my own analysis: no type-design changes in rework
- `[SEC]` security disabled via settings; my own analysis: input validation strengthened by from_npc boundary check, no new attack surface
- `[SIMPLE]` TEA verify simplify fan-out clean across all 3 lenses; no new findings from rework
- `[RULE]` rule-checker: 2 LOW findings — `.get()` inconsistency line 602, inline imports of span constants (dup with test-analyzer)

**Blocking Findings:** 0
**Non-Blocking Findings:** 4 (1 MEDIUM, 3 LOW) — logged in Delivery Findings as Improvements

**Handoff:** To SM (The Mad Hatter) for finish-story.

## Notes

- Story 50-7 depends on story 50-5 (discover_clue wiring) per the dependency chain
- Story 50-8 (AccusationEvaluator) depends on this story and will need gossip state available
- GossipEngine is part of the larger scenario subsystem (ADR-053) — coordinate with the scenario clue/gossip/accusation workflow
- Reference the tea_and_murder genre pack for example gossip scenarios (recruitment, scandal, social reputation)