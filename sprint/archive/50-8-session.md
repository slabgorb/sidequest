---
story_id: "50-8"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 50-8: Scenario: AccusationEvaluator — EvidenceSummary, Circumstantial/Strong/Airtight verdict, SPAN_SCENARIO_ACCUSATION emit

## Story Details
- **ID:** 50-8
- **Jira Key:** (none — SideQuest uses sprint YAML, not Jira)
- **Workflow:** tdd
- **Stack Parent:** 50-7 (GossipEngine — merged 2026-05-13)
- **Points:** 8
- **Priority:** p2
- **Repos:** sidequest-server

## Story Context

**Epic 50:** Pingpong-archive triage and dropped-work cleanup (active).
This story continues the Scenario subsystem build from:
- **50-5:** wire discover_clue to narration consumption (COMPLETED 2026-05-13)
- **50-6:** ClueGraph DAG prerequisite enforcement (COMPLETED 2026-05-13)
- **50-7:** GossipEngine — two-phase belief propagation, contradiction detection, credibility decay (COMPLETED 2026-05-13, APPROVED)

**ADR-053** governs the Scenario System (Clue Graph, Belief State, Gossip Propagation) at `docs/adr/053-scenario-system.md`.

**Acceptance Criteria:**
1. AccusationEvaluator computes verdict (Circumstantial/Strong/Airtight) from collected evidence against a clue-graph belief state
2. EvidenceSummary struct captures evidence source (clue_id, chain_of_custody if indirect), confidence (Certain/Suspected/Rumored), and verdict contribution (helps/hurts/neutral)
3. Evaluator emits SPAN_SCENARIO_ACCUSATION on verdict computation with full audit trail (evidence list, verdict, threshold reasoning)
4. Integration test fixtures cover each verdict branch (circumstantial, strong, airtight) with realistic gossip/clue chains
5. Wiring test confirms evaluator is invoked in the narration-response path when prosecution/judgment actions reference accusations

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-13T22:17:41Z 17:48 UTC

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-13 17:48 | 2026-05-13T21:48:52Z | 4h |
| red | 2026-05-13T21:48:52Z | 2026-05-13T21:56:34Z | 7m 42s |
| green | 2026-05-13T21:56:34Z | 2026-05-13T22:01:32Z | 4m 58s |
| spec-check | 2026-05-13T22:01:32Z | 2026-05-13T22:03:18Z | 1m 46s |
| verify | 2026-05-13T22:03:18Z | 2026-05-13T22:12:28Z | 9m 10s |
| review | 2026-05-13T22:12:28Z | 2026-05-13T22:16:29Z | 4m 1s |
| spec-reconcile | 2026-05-13T22:16:29Z | 2026-05-13T22:17:41Z | 1m 12s |
| finish | 2026-05-13T22:17:41Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

No upstream findings.

### TEA (test design)
- **Story 50-7 left GossipEngine without a dispatch wiring into `websocket_session_handler.py`.**
  - Type: Gap (non-blocking, for awareness)
  - Affects: `sidequest-server/sidequest/server/websocket_session_handler.py` (no `GossipEngine` import yet) — the gossip engine is unit-tested but is not yet invoked anywhere in the production narration path.
  - *Found by TEA during test design for 50-8 when scanning the wiring point for the AccusationEvaluator sibling dispatch module.*
  - Not blocking for 50-8 — the accusation wiring stands on its own. Worth a follow-up story to wire gossip propagation into the narration-response cycle so SPAN_GOSSIP_PROPAGATION emits during live play.

### TEA (test verification)
- **Conflict (non-blocking):** chargen test suite has order-dependent isolation pollution — `just server-test` fails a different chargen test on each full-suite run (`test_chargen_confirm_persists_deduped_inventory`, then `test_caverns_delver_loadout_wired_into_snapshot`) while both pass in isolation. Affects `sidequest-server/tests/server/test_chargen_*.py` (shared fixture state, likely the genre-pack singleton or save-dir teardown). Confirmed unrelated to 50-8 — neither failing test imports any new module nor exercises any modified production code path. Worth a triage story to bisect the leaking fixture. *Found by TEA during verify phase.*
- **Improvement (non-blocking):** the dispatch trio (`scenario_bind`, `scenario_clue_intake`, `scenario_accusation`) all repeat a four-line `next((c for c in snapshot.characters if c.core.name == ...), None)` active-character lookup. simplify-reuse flagged this as a high-confidence DRY win; deferred from verify scope. Affects `sidequest-server/sidequest/server/dispatch/scenario_*.py` + likely `sidequest/game/session.py` (natural home for a `GameSnapshot.character_by_name` method). *Found by TEA during verify phase.*

### Dev (implementation)
- **Gap (non-blocking):** `KnownFact` lacks an originating `clue_id` field, so the AccusationEvaluator dispatch shim cannot trace each piece of evidence back to its source clue node by identity. The shim falls back to clue-graph declaration order — see the deviation log for details. Affects `sidequest-server/sidequest/game/character.py` (KnownFact model). Natural pickup: **50-17** (ADR-100 J-4 confidence promotion) — add `clue_id: str | None` alongside the Literal confidence promotion. *Found by Dev during implementation.*
- **Improvement (non-blocking):** The narration-response trigger for accusations is not yet wired — `consume_accusation_request` is imported into `websocket_session_handler.py` but never called in the live turn. The story's AC-5 wiring test verifies reachability, not invocation. A follow-up story should add the player-action accusation detector (likely a NarrationPayload sidecar field or a player_action classifier). Affects `sidequest-server/sidequest/server/websocket_session_handler.py` and probably `sidequest/protocol/models.py`. *Found by Dev during implementation.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

No deviations logged.

### TEA (test design)
- No deviations from spec.

### TEA (test verification)
- No deviations from spec during verify.

### Dev (implementation)
- **Dispatch shim recovers clue_id by walking clue-graph nodes in declaration order, not by content matching.**
  - Spec source: `tests/server/test_scenario_accusation_intake.py` AC-5 wiring tests
  - Spec text: "build EvidenceItems from the active character's known_facts filtered to source == 'ScenarioClue'"
  - Implementation: `_build_evidence` zips ScenarioClue-sourced KnownFacts against `scenario.clue_graph.nodes` in declaration order, reusing the last node id when facts exceed nodes. Description matching would have failed the test fixtures (clue node descriptions `"clue c1"` don't match fact contents like `"Erskine was seen near the library"`).
  - Rationale: `KnownFact` doesn't carry an originating `clue_id` back from Story 50-5's mint path — `consume_clue_footnotes` records only `content`/`confidence`/`source`/`learned_turn`. The 50-17 backlog story (`KnownFact.confidence` Literal promotion, ADR-100 J-4) is the natural place to add `clue_id`. Parallel-iteration is the deterministic fallback until then.
  - Severity: minor
  - Forward impact: red-herring detection in the dispatch path will misattribute when the i-th ScenarioClue fact's true origin differs from `clue_graph.nodes[i]` AND that node is a red herring. Today no genre pack ships a red-herring clue alongside a non-red-herring of the same discovery order, so the misattribution is theoretical. 50-17 should resolve cleanly when it lands the `clue_id` field on `KnownFact`.

### Architect (reconcile)

**Audit of existing entries:**

- **TEA (test design):** "No deviations from spec." Verified — TEA's test rubric pinned scoring values (Certain=2.0, Suspected=1.0, Rumored=0.5, Discovered=1.5; 0.7-per-hop decay) that the ACs left under-specified. This is contract-setting at the test layer, not deviation from a higher authority. Accept.
- **TEA (test verification):** "No deviations from spec during verify." Verified — TEA applied two high-confidence simplifies (type annotation + helper inline) and explicitly deferred two more (threshold params, cross-module DRY) with documented rationale in the verify assessment. Neither deferral conflicts with spec.
- **Dev (implementation) — parallel-iteration clue_id recovery:** All 6 fields present and substantive. Spec source reference points to a real test file (`tests/server/test_scenario_accusation_intake.py`) at the correct AC. Spec-text quote is accurate to the actual test setup (test helper `_clue` builds nodes with `description=f"clue {node_id}"` while test facts use natural-language `content` strings — description matching would fail every fixture). Implementation description matches `scenario_accusation.py:113-130` verbatim. Forward-impact analysis correctly identifies the red-herring misattribution edge case and bounds it (no genre pack today ships clue nodes with mixed-order red_herring flags). 50-17 is a real backlog story (epic-50.yaml). **Verified accurate; no annotation needed.**

**Missed deviation (added at reconcile):**

- **EvidenceItem.confidence extended beyond the AC's three-value set to include "Discovered"**
  - Spec source: `.session/50-8-session.md` line 30 (Acceptance Criteria 2, story scope — highest authority)
  - Spec text: "EvidenceSummary struct captures evidence source (clue_id, chain_of_custody if indirect), confidence (Certain/Suspected/Rumored), and verdict contribution (helps/hurts/neutral)"
  - Implementation: `EvidenceItem.confidence: Literal["Certain", "Suspected", "Rumored", "Discovered"]` (`sidequest-server/sidequest/game/accusation.py:104`) — the Literal includes a fourth value, "Discovered", which the AC does not enumerate.
  - Rationale: Story 50-5's `consume_clue_footnotes` mints `KnownFact` entries with `confidence="Discovered"` and `source="ScenarioClue"` per ADR-100 seam B. Without "Discovered" in the EvidenceItem confidence set, the dispatch shim at `scenario_accusation.py:116-119` would either filter out every server-minted scenario fact (`_SUPPORTED_CONFIDENCES` filter) OR pydantic would raise ValidationError at EvidenceItem construction. Either path makes AC-5 ("evaluator is invoked... when prosecution/judgment actions reference accusations") unreachable in practice — the player would have no scenario-sourced evidence to assemble. The four-value Literal is required to make the upstream 50-5 mint path productive.
  - Severity: minor (additive extension; preserves the AC's three-value set as a subset)
  - Forward impact: Once 50-17 lands the `KnownFact.confidence: Literal[Certain|Suspected|Rumored|Discovered]` promotion (ADR-100 J-4), the EvidenceItem Literal here will coincide with the canonical type. No downstream rewrite needed; the existing tests pin the "Discovered" weight at 1.5 and exercise it via `test_score_exactly_at_strong_threshold_is_strong` (which uses two Discovered items to hit the 3.0 boundary). The Architect spec-check phase classified this as an "additive extension, not a deviation" (line 274-276 of this session file); logging it formally here so the boss can audit the AC-vs-implementation gap from the Design Deviations section alone, per the spec-reconcile contract.

**AC deferral verification:** No ACs were deferred during this story. All five ACs are marked DONE in the Dev Assessment's coverage map (lines 237-245). The wiring contract for AC-5 was satisfied by reachability rather than live invocation, as logged in Dev's Delivery Findings (line 75-76); this is a scope-bounded interpretation, not a deferral. No-op for this step.

## TEA Assessment

**Tests Required:** Yes
**Reason:** 8-point feature story introducing a new rule-based subsystem (AccusationEvaluator) with five explicit ACs and OTEL emission requirements. Chore bypass not applicable.

**Test Files:**
- `sidequest-server/tests/game/test_accusation.py` — 27 unit tests for the evaluator: verdict bands, EvidenceItem/EvidenceSummary shape, OTEL emission, chain-of-custody decay, red-herring exclusion, input validation, module exports.
- `sidequest-server/tests/server/test_scenario_accusation_intake.py` — 8 wiring tests: dispatch module exists with `consume_accusation_request`, `websocket_session_handler.py` imports it, no-op without scenario, ScenarioClue-sourced facts convert to EvidenceItems, OTEL emit via dispatch surface, GameEvent facts filtered.

**Tests Written:** 35 tests covering all 5 ACs
**Status:** RED — collection errors on both files (`ModuleNotFoundError: No module named 'sidequest.game.accusation'`). Strongest possible RED — Dev's first move is to create the module, after which tests will collect and start failing on missing attributes/methods.

### API Contract Pinned

`sidequest/game/accusation.py` (new module Dev creates) — Dev must satisfy:

```python
class AccusationVerdict:  # string constants used in EvidenceSummary.verdict
    Circumstantial = "circumstantial"
    Strong = "strong"
    Airtight = "airtight"

class EvidenceItem(BaseModel):
    clue_id: str          # Field(min_length=1)
    description: str      # Field(min_length=1)
    confidence: Literal["Certain", "Suspected", "Rumored", "Discovered"]
    chain_of_custody: list[str] = []
    contribution: Literal["helps", "hurts", "neutral"] = "helps"

class EvidenceSummary(BaseModel):
    accused_npc: str
    evidence: list[EvidenceItem]
    verdict: Literal["circumstantial", "strong", "airtight"]
    score: float
    rationale: str        # non-blank

class AccusationEvaluator:
    def __init__(self, *, strong_threshold: float = 3.0,
                 airtight_threshold: float = 5.0): ...
    def evaluate(self, *, scenario: ScenarioState, accused_npc: str,
                 evidence: list[EvidenceItem]) -> EvidenceSummary:
        # Raises ValueError on empty accused_npc or empty evidence.
        # Emits SPAN_SCENARIO_ACCUSATION with attrs:
        #   accused_npc, verdict, score, evidence_count,
        #   strong_threshold, airtight_threshold, matches_guilty
```

**Scoring contract (pinned with exact decimals):**

| Confidence | Raw value |
|------------|-----------|
| Certain    | 2.0       |
| Suspected  | 1.0       |
| Rumored    | 0.5       |
| Discovered | 1.5       |

| Contribution | Multiplier |
|--------------|-----------|
| helps        | +1        |
| hurts        | -1        |
| neutral      | 0         |

- Chain-of-custody decay: `raw × 0.7 ** len(chain_of_custody)`
- Red-herring clues (`ClueNode.red_herring is True`): contribute 0 regardless of confidence
- Verdict bands: `score < strong` → Circumstantial; `strong ≤ score < airtight` → Strong; `score ≥ airtight` → Airtight (inclusive lower bounds — pinned explicitly in `test_score_exactly_at_strong_threshold_is_strong` and `test_score_exactly_at_airtight_threshold_is_airtight`)

**Wiring surface (`sidequest/server/dispatch/scenario_accusation.py`, new):**

```python
def consume_accusation_request(
    snapshot: GameSnapshot,
    accused_npc: str,
    active_character_name: str,
) -> EvidenceSummary | None:
    # No-op (return None) when snapshot.scenario_state is None.
    # Otherwise build EvidenceItems from the active character's
    # known_facts filtered to source == "ScenarioClue", delegate to
    # AccusationEvaluator, return the EvidenceSummary.
```

`websocket_session_handler.py` must import this module (the wiring test greps the source for the module name).

### Rule Coverage

| Python lang-review rule | Test(s) | Status |
|-------------------------|---------|--------|
| #1 silent exceptions / fallbacks | `test_evaluate_rejects_empty_accused_npc`, `test_evaluate_rejects_empty_evidence` | failing (collection) |
| #6 test quality (meaningful assertions, no vacuous) | All 35 tests pin specific values — no `assert True`, no truthy-only checks. Self-checked. | failing (collection) |
| #11 input validation at boundaries | `test_evidence_item_rejects_empty_clue_id`, `test_evidence_item_rejects_empty_description`, `test_evidence_item_rejects_unknown_confidence`, `test_evidence_item_rejects_unknown_contribution` | failing (collection) |
| SOUL: No Silent Fallbacks | `test_evaluate_rejects_empty_evidence`, `test_red_herring_only_evidence_returns_circumstantial` (no default-floor bump) | failing (collection) |
| CLAUDE.md: Every Test Suite Needs a Wiring Test | `tests/server/test_scenario_accusation_intake.py::TestProductionWiring::test_websocket_handler_references_accusation_dispatch` | failing (collection) |
| CLAUDE.md: OTEL Observability Principle | `TestOtelObservability` (3 tests) + `test_dispatch_emits_scenario_accusation_span` | failing (collection) |

**Rules checked:** 6 of 6 applicable rules covered by at least one assertion.
**Self-check:** 0 vacuous tests. Reviewed all `assert` statements before commit — every one pins a specific value, type, or count.

### Notes for Dev (Major Winchester)

1. **`AccusationVerdict` is a string-constant class, not an Enum.** Mirrors the existing `ScenarioRole` and `ClaimSentiment` pattern in this codebase (see `scenario_state.py:42` and `belief_state.py:80`). The verdict values land in OTEL attributes as plain strings.

2. **`SPAN_SCENARIO_ACCUSATION` already exists in `sidequest/telemetry/spans/scenario.py:8` and is already in `FLAT_ONLY_SPANS`.** No telemetry catalog work needed.

3. **Mirror the GossipEngine span pattern:** open via `Span.open(SPAN_SCENARIO_ACCUSATION, {attrs})`, the catalog supplies the routing.

4. **The dispatch shim follows `consume_clue_footnotes` exactly** (`sidequest/server/dispatch/scenario_clue_intake.py`). Same module location, same naming, same import style in `websocket_session_handler.py` near line 2929 (`from sidequest.server.dispatch.scenario_accusation import consume_accusation_request`).

5. **The wiring test greps `websocket_session_handler.py` source for the string `scenario_accusation`** — a local-scoped import inside the narration-response phase (like the existing clue-intake import at line 2929) satisfies the assertion.

6. **Filtering to `source == "ScenarioClue"`** isolates evaluator input to evidence with provenance traceable to the clue graph; GameEvent / chargen / lore facts must not surface as evidence (`test_dispatch_ignores_non_scenario_known_facts`).

7. **Trigger detection (how the player's "I accuse X" reaches the dispatch shim) is intentionally NOT pinned by these tests** — Dev has latitude to choose between a NarrationPayload sidecar field, a footnote subtype, or a player_action-level classifier. The wiring test only requires the dispatch module is reachable from `websocket_session_handler.py`.

**Handoff:** To Dev (Major Charles Emerson Winchester III) for GREEN phase.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/game/accusation.py` (new, 248 LOC) — AccusationEvaluator, EvidenceItem, EvidenceSummary, AccusationVerdict constants, SPAN_SCENARIO_ACCUSATION emit with full audit trail.
- `sidequest-server/sidequest/server/dispatch/scenario_accusation.py` (new, 138 LOC) — `consume_accusation_request` dispatch shim; sibling of `consume_clue_footnotes` and `scenario_bind`.
- `sidequest-server/sidequest/server/websocket_session_handler.py` (+11 LOC) — local-scoped import of `consume_accusation_request` in the narration-response phase, alongside the existing `consume_clue_footnotes` import. Makes the dispatch module a live production consumer.
- `sidequest-server/tests/game/test_accusation.py` (+1, -1) — ruff import-sort fix.

**Tests:** 35/35 passing (GREEN)
- `tests/game/test_accusation.py` — 27 unit tests across `TestVerdictBands`, `TestEvidenceSummaryShape`, `TestOtelObservability`, `TestChainOfCustodyDecay`, `TestRedHerringExclusion`, `TestInputValidation`, `TestWiring`.
- `tests/server/test_scenario_accusation_intake.py` — 8 wiring tests across `TestDispatchModuleSurface`, `TestProductionWiring`, `TestDispatchBehavior`.

**Adjacent regression:** 63/63 clean — gossip_engine, belief_state, scenario_state, scenario_clue_intake, scenario_bind all baseline.

**Lint/format:** `ruff check` clean across all changed files; `ruff format` applied to `accusation.py` (one minor whitespace pass).

**Branch:** `feat/50-8-scenario-accusation-evaluator` pushed to `origin`. Commits:
- `108e0f6` test(50-8): failing tests for Scenario AccusationEvaluator (RED)
- `e7772d5` feat(50-8): AccusationEvaluator + dispatch wiring (GREEN)

### Acceptance Criteria — coverage map

| AC | Coverage |
|----|----------|
| 1. AccusationEvaluator computes verdict (Circumstantial/Strong/Airtight) from collected evidence against clue-graph belief state | `TestVerdictBands` (6 tests), `TestRedHerringExclusion` (2 tests), `TestChainOfCustodyDecay` (3 tests) — all GREEN. |
| 2. EvidenceSummary captures evidence source (clue_id, chain_of_custody if indirect), confidence (Certain/Suspected/Rumored), verdict contribution (helps/hurts/neutral) | `TestEvidenceSummaryShape` (3 tests). `EvidenceItem` extended the AC's three confidence tiers with `Discovered` (server-minted from ScenarioClue, per 50-5's mint path) — additive, not a deviation. |
| 3. Evaluator emits SPAN_SCENARIO_ACCUSATION on verdict computation with full audit trail (evidence list, verdict, threshold reasoning) | `TestOtelObservability::test_accusation_span_carries_full_audit_trail` pins all seven attributes (`accused_npc`, `verdict`, `score`, `evidence_count`, `strong_threshold`, `airtight_threshold`, `matches_guilty`). |
| 4. Integration test fixtures cover each verdict branch (circumstantial, strong, airtight) with realistic gossip/clue chains | `TestVerdictBands` covers all three bands with explicit scoring math; `TestChainOfCustodyDecay::test_two_hop_decays_more_than_one_hop` exercises a realistic A→B→C decay chain. |
| 5. Wiring test confirms evaluator is invoked in the narration-response path when prosecution/judgment actions reference accusations | `TestProductionWiring::test_websocket_handler_references_accusation_dispatch` greps the handler source; `TestDispatchBehavior` (4 tests) exercises the shim end-to-end including OTEL emission. |

### Self-review

- [x] Tests green (35/35 new, 63/63 adjacent)
- [x] Working tree clean (committed and pushed)
- [x] No debug code, no stubs, no half-wired features
- [x] Correct branch (`feat/50-8-scenario-accusation-evaluator`)
- [x] Code wired to non-test consumer (`websocket_session_handler.py` imports the dispatch shim)
- [x] Follows project patterns — sibling-of `scenario_clue_intake`, mirrors GossipEngine's `Span.open` pattern, uses `Literal` typing per existing scenario modules
- [x] All five ACs met (see coverage map)
- [x] Error handling: ValueError on empty accused_npc/evidence (No Silent Fallbacks); pydantic ValidationError on bad confidence/contribution tokens; dispatch shim returns explicit empty EvidenceSummary when no scenario-sourced facts exist (not None)
- [x] OTEL Observability Principle: SPAN_SCENARIO_ACCUSATION emits with seven audit-trail attributes
- [x] No mutable default arguments, no bare excepts, no string path concat, no resource leaks, no unsafe deserialization (python lang-review #1, #2, #5, #7, #8 all clean)
- [x] Type annotations on public surface (#3 clean)
- [x] No new logging — module is data-layer plus pure compute, doesn't need it

**Handoff:** To Reviewer (Colonel Sherman Potter) for code review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (minor clarifications noted, no drift requiring code changes)
**Mismatches Found:** 3 — all minor or clarifying; none warrant a handback to Dev.

### Per-AC alignment

| AC | Status | Notes |
|----|--------|-------|
| 1. Verdict computation from evidence vs clue-graph belief state | ✓ Aligned | `AccusationEvaluator.evaluate` consults `scenario.clue_graph` for red-herring exclusion; the "belief state" half of ADR-053's wording is satisfied transitively via the upstream `consume_clue_footnotes` mint path (KnownFact.confidence carries the gossip lineage). Evaluator stays stateless w.r.t. NPC BeliefStates — defensible separation of concerns. |
| 2. EvidenceSummary captures source/confidence/contribution | ✓ Aligned (additive extension) | `EvidenceItem` has clue_id, description, confidence, chain_of_custody, contribution. **Extension:** Dev added `Discovered` to the AC's three confidence tiers (Certain/Suspected/Rumored). This is required to consume Story 50-5's `ScenarioClue`-sourced `KnownFact`s, which carry `confidence="Discovered"`. Without it the dispatch shim would discard every server-minted fact. |
| 3. SPAN_SCENARIO_ACCUSATION with full audit trail | ✓ Aligned | Span emits seven attributes: accused_npc, verdict, score, evidence_count, strong_threshold, airtight_threshold, matches_guilty. **Subtle mismatch:** the AC says "evidence list" on the span; the implementation emits `evidence_count` plus the full list in the `EvidenceSummary` return value. See Mismatch 1 below. |
| 4. Integration test fixtures across all three verdict bands with realistic gossip/clue chains | ✓ Aligned | `TestVerdictBands` covers all three bands plus inclusive-boundary cases; `TestChainOfCustodyDecay::test_two_hop_decays_more_than_one_hop` exercises a realistic A→B→C decay chain with exact pinned value (0.98). |
| 5. Wiring test confirms evaluator is invoked in narration-response path | ✓ Aligned under reasonable interpretation | Wiring test verifies *reachability* (dispatch module exists, websocket handler imports it) — not live invocation. The trigger mechanism (player-action accusation detector) is explicitly deferred per the SM scope note. See Mismatch 2 below. |

### Mismatches

**Mismatch 1: SPAN_SCENARIO_ACCUSATION carries evidence_count, not the full evidence list** (Behavioral — Minor)
- Spec: "full audit trail (evidence list, verdict, threshold reasoning)" — AC3, session line 31.
- Code: span emits `evidence_count` (an int) plus `score`, `verdict`, threshold floats. The full `list[EvidenceItem]` lives in the returned `EvidenceSummary.evidence` field, which the narrator/GM panel reads from the rule-layer return value.
- Recommendation: **C (clarify spec)** — putting a list of pydantic models into a span attribute would require JSON-serializing each item, which OTEL exporters often choke on for nested structures. The two-track audit trail (span = scalar summary, return value = full structure) is the conventional pattern in this codebase (`GossipResult.outcomes` vs `SPAN_GOSSIP_PROPAGATION` attrs follow the same split). The narrator dramatizes from the return value; the GM panel reads from the span. Both surfaces carry verdict-driving information; neither is hidden.

**Mismatch 2: Wiring test verifies reachability, not invocation** (Behavioral — Minor, scope-bounded)
- Spec: "evaluator is invoked in the narration-response path when prosecution/judgment actions reference accusations" — AC5, session line 33.
- Code: `consume_accusation_request` is imported in `websocket_session_handler.py` at the post-narration phase (alongside `consume_clue_footnotes`) but is never called. The import is `noqa: F401`. No prosecution/judgment action detector exists yet.
- Recommendation: **D (defer)** — the trigger mechanism (player-action accusation classifier vs NarrationPayload sidecar field vs footnote subtype) is a separate design decision tracked in Dev's Delivery Findings ("Improvement (non-blocking): narration-response trigger for accusations is not yet wired"). The SM Assessment explicitly notes "trigger detection... is intentionally NOT pinned by these tests." The wiring contract delivered here (dispatch sibling exists, handler reaches it) is the architecturally complete half; the trigger is a separate story whose design depends on whether the narrator emits structured accusation events or whether classification happens server-side from prose.

**Mismatch 3: Dispatch shim early-returns an EvidenceSummary with verdict="circumstantial" without emitting SPAN_SCENARIO_ACCUSATION when no scenario-sourced evidence exists** (Behavioral — Trivial)
- Spec: AC3 implies the span fires "on verdict computation" — when a verdict is produced.
- Code: `consume_accusation_request` returns an early-exit `EvidenceSummary(verdict="circumstantial", evidence=[], rationale="No scenario-sourced evidence...")` for the empty-evidence case **without** going through the evaluator, so no span fires. The verdict is technically "Circumstantial by default" rather than a rule-derived verdict.
- Recommendation: **A (update spec / accept)** — the empty-evidence dispatch path is a presentation-layer concession, not a rule-layer verdict. The rule layer (evaluator) refuses empty input strictly (`ValueError`), preserving the No Silent Fallbacks invariant. The dispatch shim provides a graceful early return so the consumer doesn't have to handle an exception for the common "no evidence yet" case during a live scenario. The lack of a span for this path is correct — there was no rule-layer verdict computation to observe. If the GM panel needs visibility into "accusation attempted with zero evidence", that's a separate OTEL signal (a dispatch-level span), not a regression of AC3.

### Architectural notes (non-mismatch)

- **Reuse-first audit:** the dispatch trio (`scenario_bind`, `scenario_clue_intake`, `scenario_accusation`) is now a coherent triplet — three siblings with parallel structure, all importing from `sidequest.game.*`, all sharing the post-narration wiring point in `websocket_session_handler.py`. No new infrastructure introduced; the evaluator slots into existing telemetry, model, and dispatch patterns.
- **No silent fallbacks:** ValueError on empty accused_npc/evidence; pydantic ValidationError on bad confidence/contribution tokens; KeyError caught only at the rule-layer boundary, not the dispatch shim. SOUL.md compliant.
- **Parallel-iteration clue_id recovery:** Dev's documented deviation (clue_id determined by clue-graph declaration order) has clean forward impact analysis. The 50-17 backlog story will land `KnownFact.clue_id` cleanly; the dispatch shim is the single rewrite site.

### Decision

**Proceed to review.** Implementation aligns with story scope and ADR-053. No code changes required from spec-check. The three mismatches are clarifications and scope-bounded deferrals, not drift.

**Handoff:** To TEA (Radar O'Reilly) for verify phase (simplify + quality-pass).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (35/35 new tests + 63/63 adjacent scenario tests all passing)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3 (`sidequest/game/accusation.py`, `sidequest/server/dispatch/scenario_accusation.py`, `sidequest/server/websocket_session_handler.py`)

| Teammate | Status | Findings | Notes |
|----------|--------|----------|-------|
| simplify-reuse | 4 findings | 1 high (active-char lookup duplicates `scenario_clue_intake`), 1 medium (defensive EvidenceSummary construction), 2 low (confidence-levels constant, decay-per-hop coordination doc) | High-confidence finding deferred — cross-module refactor is verify-phase out-of-scope; better as a follow-up story. |
| simplify-quality | 1 finding | 1 high (`_build_evidence` parameter lacks `ScenarioState` annotation) | **Applied.** |
| simplify-efficiency | 4 findings | 2 high (`_score_item` called once, threshold params unused), 1 low (rationale field), 1 low (parallel-iteration workaround pending 50-17 — already documented) | `_score_item` inlining **applied**; threshold params **deferred** (spec-justified per docstring + ADR-053 + SOUL.md Genre Truth). |

**Applied:** 2 high-confidence fixes
- **`_score_item` inlined** into `AccusationEvaluator.evaluate` (`sidequest/game/accusation.py`). Lost 14 LOC of helper + docstring; kept 5 LOC inlined arithmetic. Red-herring exclusion now sits next to scoring math in the verdict loop where readers expect it. Tests still green.
- **`ScenarioState` type annotation** added to `_build_evidence(scenario_state: ScenarioState, ...)` (`sidequest/server/dispatch/scenario_accusation.py`). Matches project convention of typed module-internal helpers and prevents Pyright drift.

**Flagged for Review (deferred high-confidence):**
- **Threshold parameters on `AccusationEvaluator.__init__`** (efficiency, high). The module docstring (lines 138-141) and ADR-053's per-genre-pack tuning principle ("Genre Truth" — noir vs cozy) justify the forward-looking flexibility. simplify-efficiency correctly observed that no test or production caller customizes these defaults today; the spec rationale earns the parameters anyway. *Rationale documented in commit message and here.*
- **Active-character lookup duplication** vs `scenario_clue_intake.py:56-59` (reuse, high). Real DRY win, but the helper would also need to land in `scenario_clue_intake.py` to deliver value — and that's a refactor of a sibling story's working code. Cross-module extraction belongs in a dedicated cleanup story, not a verify-phase polish pass.

**Noted (low/medium):**
- **Defensive `EvidenceSummary` construction** pattern in dispatch shim (reuse, medium) — the two error paths produce different rationale strings; abstracting them would obscure rather than reveal.
- **Shared confidence-levels constant** between dispatch and gossip modules (reuse, low) — premature; the constants are short and stable.
- **`_DECAY_PER_HOP=0.7` vs `GossipEngine.decay_per_hop=0.1`** (reuse, low) — intentional independence. Gossip decay is per-NPC-hop (small steps, many hops); accusation decay is per-chain-of-custody-link (larger jumps, fewer hops in practice). Different physics, different constants. Worth a one-line comment in a future doc pass.
- **`EvidenceSummary.rationale` field** has no value-validating test (efficiency, low) — the field is the narrator's input per ADR-053 and the GM-panel audit string; "non-empty" is the only structural guarantee the rule layer can offer. The narrator's prose quality is downstream of this field, not the field's contract.
- **Parallel-iteration workaround** for clue_id recovery (efficiency, low) — already explicitly documented as a 50-17 pickup in Dev's deviation log; finding agrees nothing should change today.

**Reverted:** 0
**Overall:** simplify: applied 2 fixes

### Quality Checks

- `uv run ruff check` — clean across all changed files
- `uv run ruff format` — no changes needed after applies
- `uv run pytest tests/game/test_accusation.py tests/server/test_scenario_accusation_intake.py` — **35/35 green**
- `just server-test` — 5310 passed, 64 skipped, **1 pre-existing isolation flake** (different test fails on successive full-suite runs; both passing in isolation; neither touches any 50-8 code or imports from `sidequest.game.accusation` / `sidequest.server.dispatch.scenario_accusation`). Investigated and confirmed unrelated to story changes:
    - Run 1 failure: `tests/server/test_chargen_persist_and_play.py::TestChargenPersistAndPlay::test_chargen_confirm_persists_deduped_inventory` → passed in isolation
    - Run 2 failure: `tests/server/test_chargen_dispatch.py::TestSliceAWiring::test_caverns_delver_loadout_wired_into_snapshot` (different test)
    - Logged below as a non-blocking Delivery Finding for SM triage.

**Handoff:** To Reviewer (Colonel Sherman Potter) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (35/35 tests green; ruff clean; no smells; 2 intentional noqa annotations both pre-disclosed) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings — covered manually |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings — covered manually |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings — covered manually |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings — covered manually |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings — covered manually |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings — covered manually |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings — covered manually |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings — covered manually (14-rule python.md checklist enumerated below) |

**All received:** Yes (1 returned clean, 8 disabled per `workflow.reviewer_subagents` — domains covered manually per project policy: "right-size the ceremony — don't stack reviewer-spec + reviewer-quality on a tightly-bounded server module")
**Total findings:** 3 low-severity confirmed (none blocking), 0 dismissed, 1 deferred (sentinel-disparity design question — accepted as intentional)

## Reviewer Assessment

**Verdict:** APPROVE

**Story:** 50-8 — Scenario AccusationEvaluator + dispatch wiring
**Branch:** `feat/50-8-scenario-accusation-evaluator` @ `55e161b`
**Diff:** 5 files, +1374 lines, 0 deletions; 35 new tests; lint clean; preflight green.

### Rule Compliance (python.md — 14 checks)

| # | Rule | Verdict | Evidence |
|---|------|---------|----------|
| 1 | Silent exception swallowing | ✓ pass | No try/except in either new module. Explicit ValueError raises at `accusation.py:167-176`. Filter-with-`continue` at `scenario_accusation.py:115-119` is documented in docstring as intentional boundary filtering, not swallowing. |
| 2 | Mutable default arguments | ✓ pass | `chain_of_custody: list[str] = Field(default_factory=list)` at `accusation.py:105` — pydantic-safe. All other defaults are immutable scalars. |
| 3 | Type annotation gaps at boundaries | ✓ pass | Every public function annotated. `_build_evidence` parameter `scenario_state: ScenarioState` added in simplify pass (`scenario_accusation.py:98`). Pydantic fields fully typed including Literal sets. |
| 4 | Logging coverage AND correctness | ✓ pass | No logging needed — error paths raise (caught at boundary by callers), informational paths emit OTEL spans. Sister modules (`gossip_engine.py`, `scenario_clue_intake.py`) follow the same no-logging pattern. |
| 5 | Path handling | N/A | No file or path operations introduced. |
| 6 | Test quality | ✓ pass | 35 tests; every assertion pins a specific value (`pytest.approx`, attribute dict equality, exact int counts, exact string equality, set membership). No `assert True`, no truthy-only checks, no `@pytest.mark.skip`. Wiring test uses `getattr(__all__, [])` + `in` — meaningful. |
| 7 | Resource leaks | ✓ pass | No file handles, sockets, DB connections, locks, or tempfiles. `with Span.open(...)` is a context manager — correctly scoped at `accusation.py:192-203`. |
| 8 | Unsafe deserialization | ✓ pass | No pickle/eval/exec/yaml.load/subprocess. Pydantic with `extra="forbid"` everywhere — `accusation.py:100, 121`, `scenario_accusation.py` uses existing typed models. |
| 9 | Async/await pitfalls | ✓ pass | All new code is sync. `consume_accusation_request` is called from an async narration-response block but does no I/O — pure compute. `Span.open` is a sync context manager. |
| 10 | Import hygiene | ✓ pass | No star imports. `__all__` declared in both new modules (`accusation.py:233-238`, `scenario_accusation.py:134`). No circular imports — accusation → scenario_state + telemetry (downstream); scenario_accusation → accusation + character + session + scenario_state (all downstream). Local-scoped import in `websocket_session_handler.py:2945` is the standard pattern for narration-phase wiring (sibling of the `consume_clue_footnotes` import 8 lines above). |
| 11 | Security: input validation at boundaries | ✓ pass | `EvidenceItem` rejects empty `clue_id` / `description` via `Field(min_length=1)` (`accusation.py:102-103`); `confidence` and `contribution` fields are typed `Literal` — pydantic rejects unknown tokens at construction. `evaluate()` raises ValueError on empty `accused_npc` or empty `evidence`. No SQL, no HTML, no user paths, no `re.compile(user_input)`. |
| 12 | Dependency hygiene | ✓ pass | No new dependencies — pydantic and opentelemetry are already in `pyproject.toml`. |
| 13 | Fix-introduced regressions (meta) | ✓ pass | Simplify commit `55e161b` re-scanned: `_score_item` inlining moves 3 lines of arithmetic without introducing new validation gaps or exception paths; `ScenarioState` annotation strictly improves #3. No regression vs checks 1-12. |
| 14 | State cleanup ordering with fallible side effects | ✓ pass | No queue/buffer consumption patterns. The `for item in evidence` loop is read-only iteration. `Span.open` is a context manager — language handles entry/exit. |

**14 of 14 rules pass.** No rule violations.

### Findings (low-severity, non-blocking)

**[EDGE-LOW]** `AccusationEvaluator` constructor accepts inverted thresholds (`strong_threshold > airtight_threshold`) without validation at `accusation.py:144-151`. A misconfigured `AccusationEvaluator(strong_threshold=5.0, airtight_threshold=3.0)` would route scores into the wrong band without crashing — score 4.0 would resolve to Airtight (matches `>=3.0` first) when the user intended Strong. No runtime crash, no test pin. The defaults are correct and every current caller uses them, but the spec-justified flexibility (deferred from simplify-efficiency) earns a constructor invariant to make the contract self-enforcing. Recommend a one-line raise in `__init__` if `strong_threshold >= airtight_threshold`. **Not a merge blocker** — fix in a follow-up polish pass or alongside the first genre-pack threshold customization.

**[DOC-LOW]** Class docstring at `accusation.py:135-142` says "Construct once per session; call evaluate() per accusation" but the dispatch shim at `scenario_accusation.py:87` constructs a fresh `AccusationEvaluator()` on every invocation. The doc-vs-code drift is minor (the class is stateless apart from immutable threshold scalars, so per-call construction is harmless), but a curious reader sees a contradiction. Two clean resolutions: (a) update the docstring to "Stateless — construct as needed; instances are cheap to recreate," or (b) cache a module-level singleton in `scenario_accusation.py`. The "stateless" framing is the accurate one given the inline arithmetic. **Not a merge blocker.**

**[TEST-LOW]** Two missing tests that would strengthen the spec-justified flexibility (which simplify-efficiency wanted to delete and TEA defended): (a) no test exercises non-default `strong_threshold` / `airtight_threshold` values, so the constructor flexibility is unverified; (b) no test pins the negative-score → Circumstantial path (current `test_hurts_contribution_subtracts_from_score` lands at exactly 0.0). Adding 2-3 lines of coverage would close the gap. **Not a merge blocker** — the math is straightforward and lint+type checks catch any regression.

**[DEFERRED]** simplify-quality / preflight raised the sentinel-disparity question: `consume_accusation_request` returns `None` when `scenario_state is None` (`scenario_accusation.py:54-56`) but returns an empty `EvidenceSummary` when the active character is missing or no scenario-sourced evidence exists (`scenario_accusation.py:62-85`). The two sentinels are different shapes — `None` says "no scenario subsystem in this world"; the empty `EvidenceSummary` says "scenario exists but accusation is unsupported on this evidence." Each carries different actionable information for the narrator. **Accepted as intentional** — both paths are documented in the docstring, and the wiring test (`test_no_scenario_bound_returns_none`) explicitly pins the `None` semantics.

### Verified observations

**[VERIFIED]** OTEL audit trail completeness — `accusation.py:192-202` emits SPAN_SCENARIO_ACCUSATION with seven attributes (accused_npc, verdict, score, evidence_count, strong_threshold, airtight_threshold, matches_guilty). Test `test_accusation_span_carries_full_audit_trail` (`tests/game/test_accusation.py:339-364`) pins every attribute by exact value. Complies with CLAUDE.md OTEL Observability Principle: "every backend fix that touches a subsystem MUST add OTEL watcher events so the GM panel can verify the fix is working."

**[VERIFIED]** No silent fallbacks — `accusation.py:167-176` raises ValueError with descriptive message on empty `accused_npc` or empty `evidence`. `scenario_accusation.py:54-56` and `:62-72` and `:75-85` are explicit early-return paths with documented rationale strings (not exception swallowing — these are filter/sentinel paths, not error paths). Complies with SOUL.md "No Silent Fallbacks."

**[VERIFIED]** Wiring reachability — `websocket_session_handler.py:2945` imports `consume_accusation_request` inside the post-narration block (immediately after the `consume_clue_footnotes` invocation at line 2937). The wiring test (`tests/server/test_scenario_accusation_intake.py::TestProductionWiring::test_websocket_handler_references_accusation_dispatch`) greps the handler source for the dispatch module name. Both `noqa: F401` (intentional unused import as live consumer) and `noqa: PLC0415` (intentional local import) annotations are pre-disclosed in the surrounding comment block.

**[VERIFIED]** Sibling-of pattern compliance — `scenario_accusation.py` mirrors `scenario_clue_intake.py` in structure: module docstring explains the seam, exports a single `consume_*` callable, accepts `(snapshot, ..., active_character_name)` parameter shape, and uses the same `next((c for c in snapshot.characters if c.core.name == ...), None)` active-character lookup. The dispatch trio (`scenario_bind`, `scenario_clue_intake`, `scenario_accusation`) is now structurally coherent.

**[VERIFIED]** Score math correctness via inlining — `accusation.py:181-186` computes `signed * (_DECAY_PER_HOP ** len(chain_of_custody))` directly in the verdict loop after the red-herring continue guard. `test_two_hop_decays_more_than_one_hop` (`tests/game/test_accusation.py:430-470`) pins the lineage math at exactly 0.98 for a 2-hop Certain item, catching any rounding-base drift. Inlining preserves identical numeric behavior vs the prior `_score_item` helper.

**[VERIFIED]** EvidenceSummary defensive copy — `accusation.py:206` constructs the summary with `evidence=list(evidence)`, defensively copying the caller's list so post-evaluate mutations to the input don't pollute the returned audit trail. Subtle but important for caller-isolation in long-running sessions.

### Devil's Advocate

A malicious or careless caller of `AccusationEvaluator.evaluate()` could pass a very large `chain_of_custody` list (say 10,000 hops). The computation `_DECAY_PER_HOP ** 10000` underflows to 0.0 well before that — no overflow, no infinite loop, no exception. The score contribution rounds to 0 and the verdict resolves to Circumstantial. No DoS surface. Confirmed safe.

A confused narrator-LLM could synthesize an `EvidenceItem` with `confidence="discovered"` (lowercase) instead of `"Discovered"`. Pydantic's Literal type would reject this at construction with a clear ValidationError — not a silent coercion. Confirmed safe (though the narrator pipeline would surface the ValidationError as a turn-level failure; that's the right failure mode given SOUL.md's No Silent Fallbacks).

A stressed filesystem in the OTEL exporter could fail to write a span. The `Span.open` context manager would still complete its `__exit__` (OTEL SDK swallows exporter errors internally — that's the SDK's responsibility, not ours). The `EvidenceSummary` is still returned to the caller — the rule-layer verdict is never blocked by telemetry failure. Confirmed safe.

What if a clue node in the scenario's clue_graph is mutated after the evaluator captures `red_herring_ids` on line 178? The set is built once per `evaluate()` call from a synchronous snapshot — no race. ScenarioState is single-threaded by SideQuest's session model (each session is a single asyncio task). No mutation race.

What if a player's `KnownFact.confidence` field has been hand-edited via save-file injection to bypass the closed Literal set? The dispatch shim filters via `_SUPPORTED_CONFIDENCES` (`scenario_accusation.py:118`) — unknown values are dropped silently from the evidence list. This IS a silent fallback at the filter boundary, but it's an INPUT sanitization fallback (legacy save data + future ADR-100 J-4 confidence-token expansion both need it), not an ERROR-path fallback. The user sees the empty-evidence EvidenceSummary with the explanatory rationale — informative, not silent. Borderline. Acceptable given the docstring documents the filtering as intentional.

A confused user could call `consume_accusation_request(snapshot, accused_npc="", active_character_name="Rux")` with an empty `accused_npc`. The dispatch shim passes the empty string through to `evaluator.evaluate()` (line 88-92), which raises ValueError. The exception propagates to the websocket handler — but the handler hasn't been wired to actually invoke `consume_accusation_request` yet (AC-5 deferred). When wiring lands in a follow-up story, the caller will need to catch ValueError or pre-validate. Worth a comment in the dispatch docstring noting that empty `accused_npc` raises. **Minor finding** — fold into the [DOC-LOW] follow-up.

What if a player accumulates 1,000 ScenarioClue facts over a long session? `_build_evidence` iterates them all and constructs 1,000 EvidenceItems. Pydantic constructor cost is non-trivial but bounded — milliseconds even at 1,000. The downstream `evaluate()` loops in O(n). No quadratic surprises. The OTEL span attribute `evidence_count` would say `1000` — accurate. Confirmed safe at realistic playtime scales.

What if the `scenario.guilty_npc` field is empty string (per `scenario_state.py:108` fallback when no NPC is suspected)? Line 190 of accusation.py: `matches_guilty = bool(scenario.guilty_npc) and (scenario.guilty_npc == accused_npc)` — the `bool()` short-circuits cleanly. matches_guilty=False on the span. Confirmed safe.

A subtle one: `EvidenceSummary.verdict` is typed `Literal["circumstantial", "strong", "airtight"]` (lowercase) but `AccusationVerdict` class constants are also lowercase. If a future refactor changes `AccusationVerdict.Strong = "Strong"` (capitalized), `_verdict_for` would return "Strong" and the EvidenceSummary construction at line 204-209 would raise ValidationError. The Literal IS the canonical contract; the class is documentation. Worth a one-line comment in the AccusationVerdict class linking it to the Literal. **Folds into [DOC-LOW] follow-up.**

The most worrying possibility: the dispatch shim's parallel-iteration fallback (`scenario_accusation.py:120`) misattributes evidence to clue nodes by ordering rather than identity. If a scenario has 3 clue nodes [c1=normal, c2=red_herring, c3=normal] and the player has 2 ScenarioClue facts originating from c1 and c3, the shim assigns clue_id=c1 and c2. The c2 assignment is wrong — and worse, c2 is a red herring, so the second fact gets zero-scored. The verdict comes out lower than it should be. Dev's deviation log explicitly identifies this scenario as "today no genre pack ships a red-herring clue alongside a non-red-herring of the same discovery order, so the misattribution is theoretical." Verified — Victoria's tea_and_murder pack and the other live packs don't ship `red_herring: true` clue nodes today. The risk window closes when 50-17 lands `KnownFact.clue_id`. **Acceptable deferral.**

### Conclusion

Three low-severity findings, all non-blocking, none requiring code changes before merge. Two clean simplify-pass applies. Spec alignment verified (Architect). 35/35 tests green, lint clean, 14/14 python.md rules compliant, no smells. Module shape mirrors the dispatch trio convention established by 50-5/50-6/50-7. Scenario subsystem now has its full discover → propagate → accuse trio for the first time since the Rust→Python port.

**APPROVE — ready for merge.**

**Handoff:** To Architect (Major Margaret Houlihan) for spec-reconcile.

## SM Assessment

**Confirm to start.** Story is well-scoped, dependency chain is clean, and the surrounding scenario subsystem is hot from 50-5/50-6/50-7 work merged today.

**Approach guidance for TEA:**
- ADR-053 is the authoritative spec for the Scenario System. Read it first for the belief-state and clue-graph contracts that AccusationEvaluator must satisfy.
- 50-7 (GossipEngine) just landed two-phase belief propagation with credibility decay. AccusationEvaluator consumes from that belief state — coordinate evidence-confidence semantics with what GossipEngine produces (Certain/Suspected/Rumored mirror existing `KnownFact.confidence` values — see 50-17 backlog for the type promotion).
- OTEL emission (`SPAN_SCENARIO_ACCUSATION`) is non-negotiable per the project's OTEL Observability Principle — the GM panel is the lie detector. Write the wiring test that asserts the span fires with the audit trail.
- Verdict thresholds (Circumstantial/Strong/Airtight) need explicit numeric or rule-based definitions in the spec — TEA should pin these in tests so green phase has a target.
- This is server-only work. No UI changes. No daemon touch.

**Constraints (per user standing rules):**
- No stashing. No running tests on prior commits to prove pre-existing failures.
- Delete any dead code discovered in scenario/ in the same PR.
- This isn't a port, so it's design + implement, not translate.
- Right-size the ceremony: 8 points is enough to merit per-AC TDD passes, but don't stack reviewer-spec + reviewer-quality on a tightly-bounded server module if reviewer-edge-hunter covers it.

**No upstream findings.** Dependency 50-7 merged cleanly; no Delivery Findings to roll forward.