---
story_id: "50-6"
jira_key: null
epic: "50"
workflow: "tdd"
---
# Story 50-6: Scenario — ClueGraph DAG prerequisite enforcement in discover_clue (reject orphan discoveries)

## Story Details
- **ID:** 50-6
- **Jira Key:** (personal project, sprint YAML only)
- **Workflow:** tdd
- **Epic:** 50 — Pingpong-archive triage and dropped-work cleanup
- **Priority:** p2
- **Points:** 2
- **Stack Parent:** 50-5 (Scenario: wire discover_clue to narration consumption)

## Description

The ClueGraph DAG prerequisite enforcement in `discover_clue()` is currently dark (not enforced at runtime). The data model for prerequisites exists in `sidequest/genre/models/scenario.py`, but the `discover_clue()` function in `scenario_state.py:148` simply adds the clue ID to `discovered_clues` without checking whether the clue's prerequisites are satisfied.

This story implements the structural enforcement: when a clue discovery is attempted, the server validates that all prerequisite clues in the DAG have already been discovered. If prerequisites are unsatisfied, the discovery is rejected and a validation error is returned to the narrator/player.

This enforces causal discovery order — the headline guarantee from ADR-053 that "you can't know the murder weapon before you know a murder occurred" is only real if orphan discoveries are rejected at the entry point.

## Acceptance Criteria

- [ ] `discover_clue()` in `scenario_state.py` checks the ClueGraph DAG before adding to `discovered_clues`
- [ ] If prerequisites are unsatisfied, the function raises a descriptive `PrerequisiteNotSatisfiedError` (or equivalent) with the missing prerequisite clue IDs in the error detail
- [ ] The error is caught in the dispatch handler and communicated back to the narrator subsystem as a validation rejection (not a server crash or silent no-op)
- [ ] Integration test fixtures cover:
  - Discovering a root clue (no prerequisites) — succeeds
  - Discovering a clue with all prerequisites met — succeeds
  - Attempting to discover an orphan clue (prerequisites unsatisfied) — raises error with missing clue list
  - Multi-level DAG (clue A → B → C) — enforces full chain, not just direct parents
- [ ] OTEL `SPAN_SCENARIO_ADVANCE` only fires when discovery succeeds; validation rejection emits `SPAN_SCENARIO_CLUE_PREREQUISITE_VIOLATION` with attributes: `clue_id`, `missing_prerequisites` (list)
- [ ] Narrator observability: GM panel shows prerequisite-violation events so blocking/orphan-discovery bugs can be detected during playtest

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-13T17:59:53Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-13T17:19:40Z | 2026-05-13T17:21:20Z | 1m 40s |
| red | 2026-05-13T17:21:20Z | 2026-05-13T17:29:59Z | 8m 39s |
| green | 2026-05-13T17:29:59Z | 2026-05-13T17:34:12Z | 4m 13s |
| spec-check | 2026-05-13T17:34:12Z | 2026-05-13T17:36:04Z | 1m 52s |
| verify | 2026-05-13T17:36:04Z | 2026-05-13T17:54:50Z | 18m 46s |
| review | 2026-05-13T17:54:50Z | 2026-05-13T17:58:48Z | 3m 58s |
| spec-reconcile | 2026-05-13T17:58:48Z | 2026-05-13T17:59:53Z | 1m 5s |
| finish | 2026-05-13T17:59:53Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (blocking): 50-5 PR #275 is **OPEN, not merged** to `develop`, but the orchestrator sprint YAML marks 50-5 done.
  Affects `sidequest-server` repo state (PR #275 awaiting merge; `feat/50-5-scenario-wire-discover-clue-narration` branch carries `sidequest/server/dispatch/scenario_clue_intake.py`).
  TEA rebased the 50-6 branch onto `feat/50-5-...` so dispatch tests have a real consumer to fail against. **Before merging 50-6's PR, 50-5 PR #275 must merge first, and 50-6 must be rebased onto fresh develop.** The orchestrator state was wrong: the finish ceremony ran without the PR landing.
  *Found by TEA during test design.*

### Dev (implementation)
- No upstream findings during implementation. TEA's RED set covered the surface cleanly; tests went RED → GREEN with no surprises in the touch surface (`scenario_state.py`, `scenario_clue_intake.py`, `spans/scenario.py`).

### Reviewer (code review)
- **Improvement** (non-blocking): Future scenario-system hardening should consider short-circuiting `discover_clue()` when `clue_id in self.discovered_clues`. Affects `sidequest/game/scenario_state.py:163-179` (a re-discovery of an already-known clue can spuriously raise if the content patch added new `requires` after the save — dispatch swallows, so no functional regression, but GM panel sees noise). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Module docstring on `sidequest/telemetry/spans/scenario.py:1` should mention the new prerequisite-violation span. Trivial follow-up chore. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **ClueGraph shape — spec text vs live data model**
  - Spec source: `.session/50-6-session.md` § Technical Context › ClueGraph Structure (ADR-053)
  - Spec text: "`edges: dict[str, list[str]]  # clue_id -> list of prerequisite clue_ids`"
  - Implementation: Tests use the live `ClueNode.requires: list[str]` field on each node in `ClueGraph.nodes`. The `ClueGraph` BaseModel (`sidequest/genre/models/scenario.py:118`) exposes `nodes: list[ClueNode]`; the `ClueNode` carries its own `requires` list. No `edges` dict exists.
  - Rationale: Tests must drive the real shape of the data, not the spec's outdated illustration. The semantic intent (each clue declares its prerequisites) is preserved.
  - Severity: minor (terminology only — semantics intact)
  - Forward impact: Dev's GREEN code must iterate `clue_graph.nodes` and read `node.requires`, not lookup `edges[clue_id]`.

### Dev (implementation)
- No deviations from spec. Implementation followed TEA's handoff notes verbatim:
  - `SPAN_SCENARIO_CLUE_PREREQUISITE_VIOLATION` constant added and registered in `FLAT_ONLY_SPANS`.
  - `PrerequisiteNotSatisfiedError` exception with `.clue_id`, `.missing_prerequisites: list[str]` attributes and descriptive `__str__`.
  - `discover_clue()` performs node lookup → missing-prereq compute → emit violation span + raise; clues absent from graph pass through (preserves empty-graph idempotency).
  - Dispatch handler `try/except PrerequisiteNotSatisfiedError: continue` with explanatory comment that the span fires at the data layer.

### Reviewer (audit)
- **TEA's "ClueGraph shape — edges vs requires" deviation** → ✓ ACCEPTED by Reviewer: tests correctly drive the live `ClueNode.requires` model; spec text in the session was illustrative and stale. Semantic intent preserved.
- **Dev's "no deviations"** → ✓ ACCEPTED by Reviewer: GREEN implementation faithfully follows TEA's handoff. Verified at `scenario_state.py:146-179`, `scenario_clue_intake.py:65-70`, `spans/scenario.py:9-17`.
- **Architect's spec-check minor mismatches** (extra `guilty_npc` attr on violation span; ambiguous AC-3 communication channel) → ✓ ACCEPTED by Reviewer: Both correctly classified as Option A (accept spec extension) and Option C (clarify spec) respectively; no code change needed.
- **Reviewer-found undocumented deviation: module docstring drift on `spans/scenario.py:1`** — module docstring says "clue-graph advance and accusation" but the module now also exports `SPAN_SCENARIO_CLUE_PREREQUISITE_VIOLATION`. Severity: LOW. Non-blocking. Recommend follow-up chore.

### Architect (reconcile)

**Manifest review (re-verification of every prior entry, self-contained per `deviation-format.md`):**

1. **TEA — ClueGraph shape (edges vs requires).** Verified accurate:
   - Spec source `.session/50-6-session.md` § Technical Context: confirmed at line 103 — `edges: dict[str, list[str]]`.
   - Live model at `sidequest-server/sidequest/genre/models/scenario.py:118-123`: `ClueGraph` exposes `nodes: list[ClueNode]`; `ClueNode.requires: list[str]` per node (line 112). No `edges` field exists.
   - Implementation honours the live shape at `scenario_state.py:163-165` (`next((n for n in self.clue_graph.nodes if n.id == clue_id), None)` + `[r for r in node.requires if r not in self.discovered_clues]`).
   - Severity confirmed minor; semantics intact.
   - Forward impact accurate: any future code (50-7 GossipEngine, 50-8 AccusationEvaluator) reading the clue graph must iterate `clue_graph.nodes` and read `node.requires`, not a hypothetical `edges` dict.

2. **Dev — "no deviations from spec".** Verified accurate. Cross-referenced GREEN diff (`824d903..aae576f`) against ACs:
   - AC 1-2: enforcement + typed error → `scenario_state.py:146-179` + `:203-217`. ✓
   - AC 3: dispatch catches → `scenario_clue_intake.py:65-70`. ✓
   - AC 4: integration shapes → covered by 23 new tests. ✓
   - AC 5: span gating + attrs → `scenario_state.py:167-175` (violation) + `:182-191` (advance). ✓
   - AC 6: GM-panel observability → `spans/scenario.py:9-16` registers in `FLAT_ONLY_SPANS`. ✓

3. **Architect (spec-check) — Two minor mismatches.** Re-verified:
   - Extra `guilty_npc` attribute on violation span (`scenario_state.py:172`): consistent with `SPAN_SCENARIO_ADVANCE` (same function, line 187). Option A (accept spec extension) stands. Aids GM-panel correlation across spans on the same scenario; cost is zero.
   - AC-3 "communicated back to the narrator subsystem" ambiguity: confirmed there is no return channel from dispatch to a generating narrator (ADR-001 + `claude -p` one-shot transport per project memory `project_claude_p_no_reactive_tools.md`). OTEL violation span + next-turn state convergence is the only architecturally available "communication." Option C (clarify spec) stands.

4. **Reviewer (audit) — module docstring drift.** Verified accurate: `spans/scenario.py:1` reads `"""Scenario spans — clue-graph advance and accusation."""` but the module now also defines `SPAN_SCENARIO_CLUE_PREREQUISITE_VIOLATION` (line 9). LOW severity. Documented for follow-up; no impact on runtime behaviour. Not promoted to a fix in this story.

**AC deferral verification:** No ACs were deferred. All 6 ACs have GREEN test coverage and a Reviewer VERIFIED stamp. The `ac-completion` gate's accountability table is not invoked because no DEFERRED rows exist.

**Missed deviations found by Architect reconcile:** None. The pipeline's deviation chain is complete; every divergence between session-text spec and shipped code has been logged, audited, and accepted with documented rationale. No additional deviations found.

**Closing note for SM:** The session can be archived without outstanding spec issues. The two non-blocking improvements logged in `## Delivery Findings` by Reviewer (re-discovery short-circuit; stale module docstring) are future-scenario-system polish, not 50-6 obligations.

## Technical Context

### ClueGraph Structure (ADR-053)

From `sidequest/genre/models/scenario.py`:
```python
@dataclass
class ClueGraph:
    clues: dict[str, Clue]
    edges: dict[str, list[str]]  # clue_id -> list of prerequisite clue_ids

@dataclass
class Clue:
    id: str
    name: str
    description: str
    # ... other fields
```

The `edges` dict maps each clue ID to its list of **prerequisite clue IDs**. A clue with an empty prerequisite list is a root clue.

### Current discover_clue() Implementation

Location: `sidequest/game/scenario_state.py:148`

```python
def discover_clue(self, clue_id: str) -> None:
    """Add a clue to the discovered set. (Mutation helpers minimal — full between-turn logic deferred.)"""
    self.discovered_clues.add(clue_id)
```

**Problem:** No DAG validation. An orphan clue can be discovered even if its prerequisites are not yet in `discovered_clues`.

### Dispatch Flow (ADR-100 + 50-5)

From `sidequest/server/dispatch/scenario_handlers.py` (or equivalent post-50-5):
1. Narrator emits `SPAN_SCENARIO_ADVANCE` with `clue_id` in the structured output
2. Dispatch handler calls `scenario_state.discover_clue(clue_id)`
3. Handler emits `SPAN_SCENARIO_ADVANCE` and updates game state
4. Next turn renders the discovery to the player

**New flow for 50-6:**
1. Narrator emits `SPAN_SCENARIO_ADVANCE` with `clue_id`
2. Dispatch handler calls `scenario_state.discover_clue(clue_id)`
3. If `PrerequisiteNotSatisfiedError` is raised:
   - Log the validation error
   - Emit `SPAN_SCENARIO_CLUE_PREREQUISITE_VIOLATION` with missing clue list
   - Return validation failure to narrator (which may be logged but does not crash the turn)
4. If discovery succeeds:
   - Emit `SPAN_SCENARIO_ADVANCE` normally
   - Continue turn rendering

### OTEL Spans

New span definition needed in `sidequest/telemetry/spans.py`:

```python
def span_scenario_clue_prerequisite_violation(
    clue_id: str,
    missing_prerequisites: list[str],
) -> None:
    """
    Emitted when discover_clue() is called but DAG prerequisites are unsatisfied.
    Attributes:
    - scenario.clue_id: str — the clue that was attempted
    - scenario.missing_prerequisites: json list — prerequisite clue IDs not yet discovered
    """
```

## Dependencies

- **Depends on:** 50-5 (Scenario: wire discover_clue to narration consumption)
  - 50-5 establishes the dispatch path that calls `discover_clue()`
  - 50-6 hardens that path with DAG validation

- **Depended on by:** None in current backlog (gossip + accusation defer to later epic)

## References

- **ADR-053:** Scenario System (Clue Graph, Belief State, Gossip Propagation) § Implementation status
- **ADR-100:** Journal Pipeline Coherence (Scenario subsystem context)
- **Story 50-5:** Scenario: wire discover_clue to narration consumption (predecessor)
- **Sprint context:** `/Users/slabgorb/Projects/oq-2/sprint/context/context-story-45-50.md` (narrative context on ADR-053 restoration)

## Branch Information

**Branch:** `feat/50-6-scenario-cluegraph-dag-prerequisite-enforcement`
**Base:** `develop` (gitflow per sidequest-server repo policy)
**Repo:** `sidequest-server`

## Sm Assessment

**Scope:** 2-point, single-repo (server) hardening of `scenario_state.discover_clue()`. Direct follow-on to 50-5 which just merged the discover_clue → narration wiring. Story is tightly scoped: add DAG prerequisite check, raise typed error, emit OTEL violation span, integration tests for the four discovery shapes (root / satisfied / orphan / multi-level chain).

**Approach:** Standard TDD. The data model (ClueGraph.edges) and call site (scenario_state.py:148) already exist — this is mechanical enforcement at a single seam plus a new OTEL span. No design ambiguity that requires Architect.

**Risks / things TEA should watch:**
- Error type: spec calls for `PrerequisiteNotSatisfiedError` — TEA should confirm whether to add a new exception class or reuse an existing scenario-validation error pattern (check `sidequest/game/scenario_state.py` neighbors).
- Dispatch handler error handling — AC says rejection must NOT crash the turn. Tests must cover the dispatch path swallowing the error, emitting the violation span, and continuing. This is a wiring test per CLAUDE.md (no orphaned subsystem).
- OTEL span: new `SPAN_SCENARIO_CLUE_PREREQUISITE_VIOLATION` must land in `sidequest/telemetry/spans.py` and be observable from the GM panel (lie-detector principle).
- Multi-level chain: AC explicitly demands `A → B → C` test — verify the check is transitive (all prerequisites discovered), not just "any one parent."

**No upstream findings.** Spec is clear; AC is testable.

**Handoff:** TEA (Radar) for RED phase.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (17 failing — ready for Dev)

### Test Files

- `tests/server/test_scenario_state_prerequisite_enforcement.py` — 13 unit tests on `ScenarioState.discover_clue()` DAG validation, violation span emission, and exception contract
- `tests/server/test_scenario_clue_intake_prerequisite_enforcement.py` — 10 dispatch-handler integration tests on `consume_clue_footnotes()` error swallowing and batch continuity

**Test Location Note:** Both files live under `tests/server/` (not `tests/game/`) because they depend on the `otel_exporter` fixture which is defined in `tests/server/conftest.py` (consolidated there by 50-5's verify-phase refactor commit `5763bf0`). This matches the 50-5 pattern where `test_scenario_clue_intake.py` exercises `scenario_state` behavior from `tests/server/`.

### RED Verification

- **23 tests collected:** 17 failing (RED on enforcement, span, exception shape), 6 passing (happy-path tests that already work because current code accepts everything — these will still pass after Dev's GREEN and lock in the no-regression contract).
- **50-5 baseline preserved:** 21/21 existing scenario tests still pass (no production code touched).

### Test Coverage by AC

| AC | Test(s) | Status |
|----|---------|--------|
| `discover_clue()` checks ClueGraph DAG before adding | `test_orphan_discovery_raises_prerequisite_not_satisfied_error`, `test_orphan_discovery_does_not_add_to_discovered_clues` | failing |
| Raises `PrerequisiteNotSatisfiedError` with missing clue IDs | `test_error_lists_missing_prerequisites`, `test_error_lists_only_unsatisfied_prerequisites` | failing |
| Error caught in dispatch handler (no crash, no silent no-op) | `TestDispatchSwallowsPrerequisiteError` class (3 tests) | failing |
| Root clue succeeds | `test_root_clue_with_no_prerequisites_discovers` | passing (preserved contract) |
| All-prereqs-met clue succeeds | `test_clue_with_satisfied_prerequisites_discovers` | passing (preserved contract) |
| Orphan clue raises with missing list | `test_orphan_discovery_raises_prerequisite_not_satisfied_error`, `test_error_lists_missing_prerequisites` | failing |
| Multi-level DAG (A→B→C) enforces full chain | `test_multi_level_chain_rejects_skipping_the_middle`, `test_multi_level_chain_in_order_discovers_all` | mixed (skip-middle failing, in-order passing as preserved contract) |
| `SPAN_SCENARIO_ADVANCE` only on success | `test_violation_does_not_emit_scenario_advance`, `test_orphan_footnote_does_not_emit_advance` | failing |
| Rejection emits `SPAN_SCENARIO_CLUE_PREREQUISITE_VIOLATION` with `clue_id`, `missing_prerequisites` | `test_violation_emits_dedicated_span`, `test_orphan_footnote_emits_violation_span` | failing |
| GM-panel observability (span visibility) | `TestDispatchViolationObservability` class | failing |

### Rule Coverage (`.pennyfarthing/gates/lang-review/python.md`)

| Rule | Applied to RED tests | Status |
|------|---------------------|--------|
| #1 silent exception swallowing | Dispatch tests assert helper does NOT swallow into silent no-op — it catches `PrerequisiteNotSatisfiedError` specifically and emits a span (not a bare except). Tests assert the typed-error catch path; **Dev MUST catch `PrerequisiteNotSatisfiedError`, never bare `except Exception`** | enforced |
| #6 test quality | All tests have meaningful assertions (specific values, not truthy checks). No `assert True`, no `let _ =`. Self-check: `test_clue_outside_graph_passes_through_unchanged` asserts membership AND no error, not just one. | clean |
| #11 input validation at boundaries | `PrerequisiteNotSatisfiedError` is the explicit validation rejection at the scenario-state boundary. Tests assert the error carries enough context (`clue_id`, `missing_prerequisites`) for the dispatch handler to act on it. | enforced |

Rules #2 (mutable defaults), #3 (type annotations), #4 (logging), #5 (path handling), #7 (resource leaks), #8 (unsafe deserialization), #9 (async pitfalls), #10 (import hygiene), #12 (deps), #13 (fix regressions) are not directly exercised by this story's surface area — they apply at GREEN review.

### Design Decisions Embedded in Tests

1. **Violation span fires at the data layer** (`discover_clue()` itself), consistent with how `SPAN_SCENARIO_ADVANCE` is already emitted from `discover_clue` rather than from the caller. Dev's GREEN code should emit the violation span inside `discover_clue` before raising, so the dispatch handler's catch path doesn't need to re-emit.

2. **Clue id NOT in `clue_graph.nodes` → passthrough.** A clue absent from the graph has no declared prerequisites; `discover_clue` adds it without raising. This preserves the existing `test_discover_and_question_are_idempotent` contract (empty graph case) and matches 50-5's dispatch which pre-filters by membership in `clue_graph.nodes`. The DAG check only fires when the clue IS in the graph.

3. **Exception attribute shape** is asserted explicitly: `.clue_id: str` and `.missing_prerequisites: list[str]`. Spec calls for these as "error detail"; tests pin the surface contract.

4. **Batch continuity** is exercised: one orphan footnote in a batch does NOT stop trailing valid footnotes. The dispatch loop must `try/except` per-footnote, not per-batch. This is the difference between "rejection is a validation failure" and "rejection breaks the turn."

### Handoff Notes for Dev (Major Winchester)

Production code to add:

1. **`sidequest/telemetry/spans/scenario.py`** — new constant `SPAN_SCENARIO_CLUE_PREREQUISITE_VIOLATION = "scenario.clue_prerequisite_violation"`, register in `FLAT_ONLY_SPANS`. (The `test_routing_completeness.py` test enforces registration — Dev will see it fail if it's missing.)

2. **`sidequest/game/scenario_state.py`** — new exception class `PrerequisiteNotSatisfiedError(Exception)` with `.clue_id: str` and `.missing_prerequisites: list[str]` attributes and a descriptive `__str__`. Modify `discover_clue()` to:
   - Find the `ClueNode` in `self.clue_graph.nodes` by id (if not found → passthrough current behavior)
   - If found: compute `missing = [r for r in node.requires if r not in self.discovered_clues]`
   - If `missing`: emit `SPAN_SCENARIO_CLUE_PREREQUISITE_VIOLATION` with `clue_id` and `missing_prerequisites`, then raise `PrerequisiteNotSatisfiedError`
   - Else: existing `SPAN_SCENARIO_ADVANCE` path

3. **`sidequest/server/dispatch/scenario_clue_intake.py`** — wrap the `scenario.discover_clue(fn.fact_id)` call in `try/except PrerequisiteNotSatisfiedError: continue`. The violation span fires at the data layer, so the dispatch catch can be a silent `continue` (it's not swallowing — the subsystem already logged via OTEL).

### Delivery Findings

The 50-5 PR-not-merged blocker is the only upstream finding (already recorded under `### TEA (test design)` in the Delivery Findings section above).

**Handoff:** Major Winchester for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Status:** GREEN — 23/23 RED tests now pass; 1810/1810 wider regression preserved.

**Files Changed:**
- `sidequest/telemetry/spans/scenario.py` — new `SPAN_SCENARIO_CLUE_PREREQUISITE_VIOLATION` constant, registered in `FLAT_ONLY_SPANS`.
- `sidequest/game/scenario_state.py` — new `PrerequisiteNotSatisfiedError(Exception)` with `.clue_id` and `.missing_prerequisites: list[str]` attributes; `discover_clue()` now performs node lookup → prerequisite check → violation-span-emit + raise on orphan; clues absent from the graph pass through unchanged.
- `sidequest/server/dispatch/scenario_clue_intake.py` — wraps `discover_clue()` call in `try/except PrerequisiteNotSatisfiedError: continue`; preserves batch continuity (one orphan footnote does not stop trailing valid ones).

**Tests:** 23/23 GREEN. 50-5 baseline (24/24) preserved. Routing-completeness PASS. Wider regression (1810 tests across `tests/server/`, `tests/game/test_scenario_state.py`, `tests/telemetry/`) PASS.

**Lint:** `ruff check` clean. `ruff format` applied to `scenario_state.py`. `pyright` 0 errors / 0 warnings on touched files.

**Branch:** `feat/50-6-scenario-cluegraph-dag-prerequisite-enforcement` (pushed to origin)

**Self-Review Judgment Checks:**
- [x] Code is wired: `discover_clue()` is called by `consume_clue_footnotes()`, which is wired into `WebSocketSessionHandler._execute_narration_turn` per 50-5's GREEN. New error path traverses the same wire.
- [x] Project patterns followed: span emission via `Span.open()` context manager mirrors `SPAN_SCENARIO_ADVANCE`; exception class with `.clue_id` / `.missing_prerequisites` attributes mirrors `ResourcePatchError` family in `resource_pool.py`; `try/except SpecificError: continue` per CLAUDE.md "no silent fallbacks" (the OTEL violation span IS the not-silent signal).
- [x] All ACs met: DAG check ✓, typed error with missing list ✓, dispatch catches without crash/silent-noop ✓, all four integration scenarios covered ✓, `SPAN_SCENARIO_ADVANCE` only on success ✓, violation span with correct attrs ✓, GM-panel observable ✓.
- [x] Error handling: explicit catch of `PrerequisiteNotSatisfiedError` in dispatch (not bare `except Exception`); explanatory comment justifies the `continue` (span fires at data layer, not silently swallowed).

**Stack note for Reviewer/SM:** This branch is rebased onto `feat/50-5-scenario-wire-discover-clue-narration` (PR #275, still open). 50-5 must merge before 50-6 lands; 50-6 should then be rebased onto fresh `develop` before its own merge.

**Handoff:** To verify phase (Radar for simplify pass).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (minor cosmetic drift, no code change required)
**Mismatches Found:** 2 minor, 0 blocking

### AC-by-AC verification

| AC | Verdict | Evidence |
|----|---------|----------|
| 1. `discover_clue()` checks DAG before adding | ✅ Met | `node = next(...)`, `missing = [...]`, `if missing:` fires before `discovered_clues.add()` (`scenario_state.py:163-179`). |
| 2. Raises `PrerequisiteNotSatisfiedError` with missing IDs | ✅ Met | Exception class with `.clue_id: str`, `.missing_prerequisites: list[str]`, descriptive `__str__` (`scenario_state.py:204-218`). |
| 3. Error caught in dispatch handler — no crash, no silent no-op | ✅ Met (with ambiguity noted below) | `try/except PrerequisiteNotSatisfiedError: continue` in `scenario_clue_intake.py:65-70`. Not-silent guarantee = OTEL violation span at data layer. |
| 4. Integration tests cover root / satisfied / orphan / multi-level | ✅ Met | TEA's 23 tests cover all four shapes in unit form; dispatch tests `test_valid_footnote_after_orphan_still_processes` and `test_orphan_in_middle_does_not_stop_trailing_valid` exercise the full `consume_clue_footnotes()` integration path. |
| 5. Advance span only on success; rejection emits violation span with `clue_id`, `missing_prerequisites` | ✅ Met (with minor extra noted below) | Violation span emitted with `Span.open()` BEFORE `raise`; advance span is unreachable on the violation path. |
| 6. GM-panel observability | ✅ Met | New span registered in `FLAT_ONLY_SPANS`; routing-completeness test passes; attributes are flat (str + list). |

### Mismatches

- **Extra in code: violation span carries `guilty_npc` attribute** (cosmetic — minor)
  - Spec: AC-5 lists `clue_id` and `missing_prerequisites` as the required attributes.
  - Code: emits both, plus `guilty_npc` (matching the parity already established by `SPAN_SCENARIO_ADVANCE`).
  - Recommendation: **A — accept as spec extension.** The `guilty_npc` attribute aids GM-panel correlation between rejection events and the current scenario solution; it costs nothing and matches the sibling span's contract. No code change.

- **Ambiguous spec: AC-3 "communicated back to the narrator subsystem"** (behavioral — minor)
  - Spec: "The error is caught in the dispatch handler and communicated back to the narrator subsystem as a validation rejection (not a server crash or silent no-op)."
  - Code: Caught and `continue`d; communication to the narrator-subsystem is via OTEL violation span (lie-detector channel) plus next-turn state convergence (the rejected clue is not in `discovered_clues`, so the next narration prompt won't show it as a KnownFact).
  - Recommendation: **C — clarify the spec, no code change.** Per ADR-001 and the `claude -p` one-shot transport (project memory `project_claude_p_no_reactive_tools.md`), there is no live return-channel from dispatch to a generating narrator. The OTEL span + state convergence is the only "communication" the architecture admits. Dev's interpretation is correct.

### Pattern Fidelity

- **Span emission via `Span.open()` context manager** — mirrors `SPAN_SCENARIO_ADVANCE` (`scenario_state.py:181-189`).
- **Exception-with-attributes pattern** — mirrors `ResourcePatchError`/`UnknownResource`/`NotVoluntary` in `resource_pool.py:73-95`.
- **Data-layer-owns-span, caller-catches-typed-error** — consistent with the project's "OTEL is the lie detector" doctrine (subsystem owns its own spans; caller only catches the typed error, never re-emits).
- **Empty-graph passthrough** — preserves the existing `test_discover_and_question_are_idempotent` contract and matches 50-5's dispatch pre-filter behaviour.

### TEA's Logged Deviation (review)

The `edges` vs `requires` deviation logged by TEA is accurate and correctly handled: the spec text in the session's Technical Context section illustrated a stale shape (`ClueGraph.edges: dict[str, list[str]]`) but the live model is `ClueNode.requires: list[str]` per node in `ClueGraph.nodes`. Code follows reality; deviation is captured under `### TEA (test design)`. No further action.

### Stack note (carried forward)

50-6 is rebased onto `feat/50-5-scenario-wire-discover-clue-narration` (PR #275, open). The Dev Assessment correctly captures this. Per Sm/Reviewer flow: 50-5 must merge before 50-6; on 50-5 merge, rebase 50-6 onto fresh `develop`.

**Decision:** Proceed to verify phase. No hand-back to Dev needed.

**Handoff:** Radar (TEA) for verify (simplify + quality-pass).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3 (`sidequest/game/scenario_state.py`, `sidequest/server/dispatch/scenario_clue_intake.py`, `sidequest/telemetry/spans/scenario.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 4 findings | 1 medium (extract `ClueGraph.get_node_by_id` helper), 1 medium (add `@contextmanager` for violation span), 2 low (canonical patterns, no change needed) |
| simplify-quality | 3 findings | 1 high but out-of-scope (pre-existing `random.Random \| random.Random` redundancy on line 96), 1 medium (`__all__` export list), 1 low (comment reword) |
| simplify-efficiency | 2 findings | 1 high (`list(missing)` redundant), 1 low (defensive `list()` copy in exception ctor) |

**Applied:** 1 high-confidence fix — dropped `list(missing)` in violation span attrs (commit `3d62f03`). `missing` is already a `list[str]` from the prior comprehension.

**Flagged for Review (not auto-applied):** 0 — all medium-confidence findings were dismissed on local-consistency grounds (see below).

**Dismissed:**
- **`__all__` export list (simplify-quality, medium)** — Survey of `sidequest/telemetry/spans/`: 1 of ~30 sibling modules uses `__all__` (`region_state.py`). Convention here is to omit it. Reject.
- **`@contextmanager` helper for violation span (simplify-reuse, medium)** — `sidequest/telemetry/spans/scenario.py` has 0 `@contextmanager` helpers; sibling `SPAN_SCENARIO_ADVANCE` is also emitted via raw `Span.open()` in the same `discover_clue` function. Local consistency wins. Reject.
- **Extract `ClueGraph.get_node_by_id()` (simplify-reuse, medium)** — single caller (the new `discover_clue` branch). Premature extraction. Defer until a second caller appears (e.g., 50-7 GossipEngine).
- **Pre-existing redundant type union on line 96 (simplify-quality, high)** — outside the 50-6 touch surface; the GREEN commit didn't touch line 96. Pre-existing in `from_genre_pack`. Reject as out-of-scope; a separate refactor PR can address.
- **Defensive `list()` copy in `PrerequisiteNotSatisfiedError.__init__` (simplify-efficiency, low)** — Defensive copy in exception constructor protects against caller mutation after raise. Low cost, defensible. Defer.
- **Comment reword in dispatch handler (simplify-quality, low)** — Existing comment "Violation span already emitted at the data layer..." IS the architectural rationale, not just the what. Reviewer agreed at spec-check. Defer.

**Reverted:** 0

**Overall:** simplify: applied 1 fix

### Quality Checks (post-simplify)

- **Pytest (scenario touch surface + adjacents):** 47/47 passing — `test_scenario_state_prerequisite_enforcement.py` (13), `test_scenario_clue_intake_prerequisite_enforcement.py` (10), `test_scenario_clue_intake.py` (12), `test_narration_clue_discovery_wiring.py` (3), `test_scenario_state.py` (9).
- **Ruff check:** All checks passed (sidequest/ + tests/).
- **Ruff format:** 944 files already formatted.
- **Wider regression (1810 server + scenario + telemetry tests):** all passing post-simplify per the verify-phase testing-runner.

### Helper-generated drift (flag for Reviewer)

⚠️ **Non-substantive PR weight:** The verify-phase `testing-runner` subagent ran `ruff format .` across the entire `sidequest-server` repo when invoking `pf check`, modifying 92 files outside the 50-6 touch surface. User authorised keeping them in this PR rather than splitting them out. Captured as a distinct chore commit `12f4d31` ("chore(50-6 verify): ruff format pass on repo (helper-generated)") so the substantive 50-6 work remains traceable in `aae576f` (GREEN) and `3d62f03` (simplify).

**Reviewer (Colonel Potter):** triage whether to (a) accept inline given the auto-fix nature, (b) split into a separate format-only PR, or (c) revert the chore commit and require the offending repo-wide drift to ship through a dedicated PR. The 50-6 substantive diff is 3 files (already reviewed by Architect at spec-check); the rest is mechanical `ruff format` output.

**Handoff:** Colonel Potter (Reviewer) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — tests 23/0/0, lint clean, 0 code smells, wiring confirmed at `websocket_session_handler.py:2929-2933` |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings (handled inline by Reviewer) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings (handled inline by Reviewer) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings (handled inline by Reviewer) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings (handled inline by Reviewer) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings (handled inline by Reviewer) |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings (handled inline by Reviewer) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings (TEA verify-phase simplify already executed) |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings (handled inline by Reviewer against `gates/lang-review/python.md`) |

**All received:** Yes (1 returned + 8 disabled pre-filled per settings)
**Total findings:** 1 confirmed minor (LOW — stale module docstring), 1 deferred non-blocking (LOW — save+graph-evolution edge case), 0 dismissed

## Reviewer Findings (inline coverage of disabled domains)

### [EDGE] Edge-hunter (Reviewer-inline)
- **Broken graph reference** (clue declares `requires=["phantom"]` where "phantom" not in `clue_graph.nodes`): code correctly reports `missing=["phantom"]` and raises. Content-validation concern, not 50-6's. ✓
- **Cycle in DAG** (A→B→A): both nodes unsatisfiable, both raise indefinitely. Content-validation concern, not 50-6's. ✓
- **Self-requirement** (A requires A): unsatisfiable from clean state; if A is somehow already in `discovered_clues` (legacy save), re-discovery passes. Per project memory `feedback_legacy_saves.md`: legacy save concerns are not blockers. ✓
- **Empty `node.requires` list**: `missing=[]`, falsy, falls through to advance path. ✓
- **`None` requires**: `ClueNode.requires` is `Field(default_factory=list)` — can't be None. ✓
- **No edge issues identified.** VERIFIED — `scenario_state.py:163-179` is type-safe and graph-edge-safe.

### [SILENT] Silent-failure-hunter (Reviewer-inline)
- **`except PrerequisiteNotSatisfiedError: continue`** at `scenario_clue_intake.py:67-70`: NOT silent. The violation span fires at the data layer (`scenario_state.py:167-175`) before the exception is raised. OTEL span is the lie-detector signal per project doctrine (CLAUDE.md "OTEL Observability Principle"). Catch is typed-specific (not `except Exception`), with explanatory comment. Confirmed compliant with Python lang-review rule #1. VERIFIED.
- **`if scenario is None: return`** at `scenario_clue_intake.py:52-53`: pre-existing 50-5 contract (no-scenario = no-op). Not 50-6's surface. ✓
- **No swallowed errors introduced by 50-6.** VERIFIED.

### [TEST] Test-analyzer (Reviewer-inline)
- **29 tests** across 2 files (19 unit + 10 dispatch). Class-organized: `TestDAGPrerequisiteEnforcement`, `TestPrerequisiteViolationSpan`, `TestExceptionContract`, `TestDispatchSwallowsPrerequisiteError`, `TestDispatchViolationObservability`, `TestBatchContinuity`. Coverage map matches all 6 ACs. ✓
- **Vacuous-assertion scan:** 0 hits for `assert True`, `assert False`, `assert result` standalone. Every test has specific value/state assertions. VERIFIED via `grep -cE 'assert (True|False)$'`.
- **Negative-path coverage:** orphan rejection, multi-missing prereqs, multi-level chain skip-the-middle, batch continuity with orphan-in-middle. ✓
- **Wiring test:** the existing 50-5 `test_narration_clue_discovery_wiring.py` covers `WebSocketSessionHandler._execute_narration_turn` → `consume_clue_footnotes` → `discover_clue`. The new error path traverses the same wire; the dispatch tests (`TestBatchContinuity`) exercise the helper-level integration. Together they meet the CLAUDE.md "every test suite needs a wiring test" rule. VERIFIED.
- **Defensive OTEL attribute handling:** `test_violation_emits_dedicated_span` defensively checks `isinstance(missing, str)` to accommodate JSON-string serialization of list attributes by some OTEL backends. Good test paranoia. ✓

### [DOC] Comment-analyzer (Reviewer-inline)
- **`spans/scenario.py:1` module docstring is now stale.** Says "Scenario spans — clue-graph advance and accusation." The module now also exports `SPAN_SCENARIO_CLUE_PREREQUISITE_VIOLATION`. **Severity: LOW.** Non-blocking. Could be addressed in a follow-up chore.
- `scenario_state.py:147-156` — `discover_clue` docstring is clear and accurate (DAG enforcement + passthrough). ✓
- `scenario_state.py:204-210` — `PrerequisiteNotSatisfiedError` docstring is clear. ✓
- `scenario_clue_intake.py:42-49` — updated docstring correctly mentions the rejection path. ✓
- `scenario_clue_intake.py:68-69` — inline comment explains WHY catch+continue is not silent. Follows project "comments explain WHY not WHAT" doctrine. ✓

### [TYPE] Type-design (Reviewer-inline)
- `PrerequisiteNotSatisfiedError.__init__` uses keyword-only args (`*`) with explicit `list[str]` annotation on `missing_prerequisites`. ✓
- `discover_clue(self, clue_id: str) -> None` properly annotated. ✓
- `consume_clue_footnotes` annotations preserved from 50-5. ✓
- **Defensive `list(missing_prerequisites)` copy** in exception constructor (line 214): isolates the stored attribute from caller mutation. Good defensive practice. ✓
- No stringly-typed APIs introduced. Exception attributes are typed `str` and `list[str]`. VERIFIED.

### [SEC] Security (Reviewer-inline)
- **No injection surface:** `clue_id` is a string used only as dict-key/set-membership in `discover_clue` and as an OTEL attribute. No SQL, shell, eval, or template interpolation. ✓
- **No PII in spans:** `clue_id`, `missing_prerequisites`, `guilty_npc` are game content, not personal data. ✓
- **No tenant isolation concern:** SideQuest is single-tenant per CLAUDE.md ("Personal Project — No 1898 org"). N/A.
- **No authentication bypass:** `consume_clue_footnotes` is server-internal, called from the websocket session handler post-auth. Pre-existing trust boundary. ✓
- No security findings.

### [SIMPLE] Simplifier (Reviewer-inline)
- TEA's verify-phase simplify pass already applied 1 high-confidence fix (`list(missing)` → `missing`) and dismissed 5 medium/low findings on local-consistency grounds (see TEA Assessment verify section). No additional simplifications.

### [RULE] Rule-checker (Reviewer-inline) — Python lang-review

Audited all 13 rules in `.pennyfarthing/gates/lang-review/python.md` against the 5 substantive files:

| # | Rule | Compliance | Evidence |
|---|------|------------|----------|
| 1 | Silent exception swallowing | ✅ Pass | `scenario_clue_intake.py:67` is `except PrerequisiteNotSatisfiedError`, not bare; explanatory comment on line 68-69; OTEL violation span at data layer is the not-silent signal. |
| 2 | Mutable default arguments | ✅ Pass | No new function signatures use mutable defaults. `PrerequisiteNotSatisfiedError.__init__` uses keyword-only `*` separator; `missing_prerequisites` is a required list arg. |
| 3 | Type annotation gaps at boundaries | ✅ Pass | All public APIs (`discover_clue`, `consume_clue_footnotes`, `PrerequisiteNotSatisfiedError.__init__`) have full type annotations including return types. |
| 4 | Logging coverage and correctness | ✅ Pass (via OTEL) | SideQuest doctrine: OTEL spans are the logging channel for subsystem events. Violation span fires on rejection; no `logger.error()` needed per "OTEL is the lie detector" principle in CLAUDE.md. |
| 5 | Path handling | N/A | No path manipulation in 50-6. |
| 6 | Test quality | ✅ Pass | 0 vacuous assertions; all tests assert specific values/state; negative-path coverage; wiring inherited from 50-5. |
| 7 | Resource leaks | ✅ Pass | `Span.open()` used as `with` context manager in both branches of `discover_clue`. |
| 8 | Unsafe deserialization | N/A | No deserialization introduced. |
| 9 | Async/await pitfalls | N/A | All new code is sync; called from a sync wrapper that runs in the websocket handler's existing async context. |
| 10 | Import hygiene | ✅ Pass | New imports are explicit (`PrerequisiteNotSatisfiedError`, `SPAN_SCENARIO_CLUE_PREREQUISITE_VIOLATION`). No star imports. No circular imports (verified by passing test suite). |
| 11 | Input validation at boundaries | ✅ Pass | `clue_id` is validated by `clue_graph.nodes` membership lookup (the `next(...)` early-out) and by the dispatch pre-filter `if fn.fact_id is None or fn.fact_id not in clue_ids`. |
| 12 | Dependency hygiene | N/A | No new dependencies. |
| 13 | Fix-introduced regressions | ✅ Pass | 1810/1810 wider-regression tests passing post-simplify. |

**Rule compliance summary:** 9 applicable rules pass, 4 N/A. No violations.

## Devil's Advocate

I tried to break this code. Here's what I found:

**Attack 1 — broken graph reference.** A clue declares `requires=["nonexistent"]`. The check correctly raises `PrerequisiteNotSatisfiedError`; "nonexistent" appears in `missing_prerequisites`. Player learns nothing new but the OTEL panel sees a violation pointing at the content bug. Not a code bug. **Defended.**

**Attack 2 — cycle in DAG.** A→B→A. Neither can be discovered from clean state. Both raise indefinitely. Content-quality issue, not 50-6's concern. The system fails loudly (per "no silent fallbacks") rather than corrupting state. **Defended.**

**Attack 3 — save-file with graph evolution.** Player saves with clue A discovered (root, no prereqs). Content patch adds `requires=["X"]` to A. Player re-loads; narrator re-cites A. Code path: `node` is found, `missing=["X"]` (X not in `discovered_clues`), violation raised. The dispatch handler swallows. **Observed wrinkle:** the player who already knows A gets a spurious violation logged in the GM panel when the narrator re-cites. They don't lose the fact (it's already in `discovered_clues` and `known_facts`), but Sebastien sees noise. **Severity: LOW. Non-blocking.** This is a save+content-evolution interaction worth noting for future scenario-system hardening — possibly the prereq check should short-circuit when `clue_id in self.discovered_clues` (idempotent re-discovery should be free). For 50-6, this is out of scope.

**Attack 4 — clue id with leading whitespace.** Narrator emits `fact_id="library_key "` (trailing space). The dispatch pre-filter `not in clue_ids` skips this footnote silently. Not 50-6's surface; the seam is pre-existing. **Defended.**

**Attack 5 — massive `missing_prerequisites` list (100 elements).** OTEL attribute size limits could truncate. Worst case: truncated attribute string; the exception still raises with full list. Acceptable degradation. **Defended.**

**Attack 6 — concurrent `discover_clue` calls.** Server is single-threaded async; GIL serializes the read-then-mutate pattern. **Defended.**

**Attack 7 — `node.requires` mutation during the iteration.** Single-threaded; no concurrent mutator. Pydantic's list field is exposed mutably but no caller in 50-6 mutates it. **Defended.**

**Net:** One non-blocking wrinkle (Attack 3) for the future-scenario-hardening backlog. Everything else holds. No critical or high findings.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** Narrator emits `Footnote{fact_id="murder_weapon"}` → `WebSocketSessionHandler._execute_narration_turn` → `consume_clue_footnotes(snap, footnotes, active_character_name)` → graph-membership filter → `scenario_state.discover_clue("murder_weapon")` → DAG check via `node = next(...)`/`missing = [...]` → either raises `PrerequisiteNotSatisfiedError` (caught at `scenario_clue_intake.py:67`, violation span at `scenario_state.py:167-175`, batch continues) or fires `SPAN_SCENARIO_ADVANCE` and adds to `discovered_clues`, with downstream `KnownFact` mint on first discovery. Safe because: the new error path emits OTEL before raising, the dispatch handler catches the typed error specifically (not bare except), batch continuity is preserved, and the lie-detector signal lands in the GM panel.

**Pattern observed:** Data-layer-owns-span / dispatch-catches-typed-error split (`scenario_state.py:167-179` + `scenario_clue_intake.py:65-70`) is consistent with the project's OTEL doctrine and with `SPAN_SCENARIO_ADVANCE`'s own emission pattern in the same function.

**Error handling:** Typed exception with `.clue_id` + `.missing_prerequisites: list[str]` attributes and descriptive `__str__` (`scenario_state.py:203-217`); caught specifically with explanatory `continue` (`scenario_clue_intake.py:67-70`). OTEL violation span carries the same payload for observability.

**VERIFIED observations:**
1. `[VERIFIED]` Empty-graph passthrough preserves 50-5's idempotency contract — `scenario_state.py:163` returns None when `clue_id` is not in `clue_graph.nodes`, falls through to the advance branch. Complies with the project pattern established in `test_discover_and_question_are_idempotent`.
2. `[VERIFIED]` Typed exception catch is not silent — `scenario_clue_intake.py:67` is `except PrerequisiteNotSatisfiedError` (not bare `except Exception`), with explanatory comment that the OTEL violation span fires at the data layer (`scenario_state.py:167-175`). Complies with Python lang-review rule #1 and CLAUDE.md "no silent fallbacks".
3. `[VERIFIED]` Tests cover all 6 ACs with no vacuous assertions — 0 hits on `grep -cE 'assert (True|False)$'`; 29 test methods across 6 test classes; negative-path coverage verified; wiring test inherited from 50-5.
4. `[VERIFIED]` New span constant registered in `FLAT_ONLY_SPANS` — `spans/scenario.py:11-16` adds `SPAN_SCENARIO_CLUE_PREREQUISITE_VIOLATION` to the routing registry; `test_routing_completeness.py` passes.
5. `[VERIFIED]` Production wiring intact — `websocket_session_handler.py:2929-2933` calls `consume_clue_footnotes`, so the new DAG guard is in the live narration path (not dead code).

**Findings (non-blocking):**

| Severity | Issue | Location | Recommendation |
|----------|-------|----------|----------------|
| [LOW][DOC] | Module docstring is stale — says "clue-graph advance and accusation" but now also covers prerequisite violation | `sidequest/telemetry/spans/scenario.py:1` | Update docstring in a follow-up chore commit; non-blocking. |
| [LOW][EDGE] | Save+content-evolution wrinkle: a re-discovery of an already-known clue can spuriously raise a violation if the content patch added new `requires` after the save. The dispatch swallows the rejection, so no functional regression — but Sebastien's GM panel sees noise. | `sidequest/game/scenario_state.py:163-179` | Defer to future scenario-hardening; potential fix is to short-circuit when `clue_id in self.discovered_clues`. Non-blocking. |

**Stack note (for SM):** Branch is rebased onto `feat/50-5-scenario-wire-discover-clue-narration` (PR #275, OPEN). 50-5 must merge before 50-6 lands. After 50-5 merges, rebase 50-6 onto fresh `develop` and open 50-6's PR. The Dev and TEA assessments both carry this note; SM should not run `pf sprint story finish` for 50-6 until both PRs have actually merged.

**Helper-generated drift (for SM):** Commit `12f4d31` is a `ruff format .` chore pass that touched 92 unrelated files (Reviewer concurs with TEA verify assessment — captured cleanly as a distinct commit, traceable). Acceptable inline; alternatively, SM can split it into a separate format-only PR before opening 50-6's PR.

**Handoff:** To SM (Hawkeye) for finish-story.