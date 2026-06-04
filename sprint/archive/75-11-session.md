---
story_id: "75-11"
jira_key: ""
epic: "75"
workflow: "tdd"
---
# Story 75-11: is_projectable() predicate — observation_pending gates projection eligibility (ADR-138 D1/D3)

## Story Details
- **ID:** 75-11
- **Jira Key:** (none — SideQuest is personal, no Jira)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 2
- **Priority:** p2

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-04T18:18:24Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T00:00:00Z | 2026-06-04T17:58:44Z | 17h 58m |
| red | 2026-06-04T17:58:44Z | 2026-06-04T18:04:26Z | 5m 42s |
| green | 2026-06-04T18:04:26Z | 2026-06-04T18:07:57Z | 3m 31s |
| review | 2026-06-04T18:07:57Z | 2026-06-04T18:14:34Z | 6m 37s |
| green | 2026-06-04T18:14:34Z | 2026-06-04T18:16:29Z | 1m 55s |
| review | 2026-06-04T18:16:29Z | 2026-06-04T18:18:24Z | 1m 55s |
| finish | 2026-06-04T18:18:24Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

No upstream findings.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): Implement `is_projectable` in `npc_pool.py` WITHOUT a top-level `import Npc` — `session.py` already imports `npc_pool.py`, so a module-level import of `Npc` creates a circular import. Duck-type on `not getattr(entity, "observation_pending", False)` (an `Npc` has no such field → `True`) or use a `TYPE_CHECKING` forward-ref + a function-local import. Affects `sidequest-server/sidequest/game/npc_pool.py` (the new predicate). *Found by TEA during test design.*
- **Gap** (non-blocking): 75-11 lands the predicate with no production consumer by ADR-138 design ("No wiring yet"). Reviewer should NOT flag this as a half-wired feature — the consumers are 75-12 (ADR-118 to_card/entity_sync) and 75-13 (ADR-135 reference projection). Affects `sidequest-server/sidequest/game/npc_pool.py`. *Found by TEA during test design.*
- **Question** (non-blocking): The ADR §D3 signature types only `NpcPoolMember`, but the 75-11 truth table requires the predicate to also accept a promoted `Npc` (→ always True). Tests therefore assume a union-accepting predicate `is_projectable(entity: NpcPoolMember | Npc) -> bool`. If Dev prefers `Npc` projectability handled at the call site instead, that is a contract change — bounce to RED. *Found by TEA during test design.*

### Dev (implementation)
- **Resolved (TEA's Question above):** I adopted the union-accepting signature `is_projectable(entity: NpcPoolMember | Npc) -> bool` — no contract change, no RED bounce. The predicate now lives at `sidequest-server/sidequest/game/npc_pool.py` beside the model. *Found by Dev during implementation.*
- **Improvement** (non-blocking): 75-12 / 75-13 are the consumers — they must `from sidequest.game.npc_pool import is_projectable` and call it (75-12 in the ADR-118 `to_card`/`entity_sync` path emitting `retrieval.npc_unratified_skipped`; 75-13 in the ADR-135 reference projection), each proving wiring by an OTEL/behaviour test per ADR-138. Affects `sidequest-server/sidequest/game/entity_card.py` / `entity_sync.py` and the ADR-135 reference projector. *Found by Dev during implementation.*
- No other upstream findings during implementation.

### Reviewer (code review)
- **Gap** (non-blocking): `ruff format --check` is red on `tests/game/test_npc_pool_is_projectable.py` — the dev-exit GREEN check ran `ruff format --check` on the production file only, so the test file's formatting slipped the gate. Affects `sidequest-server/tests/game/test_npc_pool_is_projectable.py` (run `uv run ruff format` on it). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Dev's own GREEN verification should `ruff format --check` ALL changed files (prod + tests), not just the production source — otherwise test-file reflows reach review as a red gate. Affects the dev GREEN-check habit (process, not code). *Found by Reviewer during code review.*
- No further upstream findings during confirmation review (round 2) — format fix verified, predicate source unchanged, APPROVED. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **No production-path wiring test for the predicate**
  - Spec source: sidequest-server/CLAUDE.md "Every Test Suite Needs a Wiring Test"
  - Spec text: "Every set of tests must include at least one integration test that verifies the component is wired into the system — imported, called, and reachable from production code paths."
  - Implementation: 75-11 ships the predicate with NO production consumer. The reachability assertion is an import/callable test (`test_is_projectable_is_importable_and_callable`), not a production-flow test.
  - Rationale: ADR-138 §Implementation-Stories scopes 75-11 to "predicate + unit tests … No wiring yet"; the consumers land in 75-12 (ADR-118 to_card/entity_sync) and 75-13 (ADR-135 reference projection), each proving wiring "by an OTEL/behaviour test, not a source-text grep." A production wiring test is impossible here because no consumer exists yet by design. Story scope (highest spec authority) wins over the blanket CLAUDE.md rule.
  - Severity: minor
  - Forward impact: 75-12 and 75-13 MUST each carry the behaviour/OTEL wiring test for their consumption site; this story deliberately defers it.
- **Type-annotation rule (#3) asserted by presence, not runtime resolution**
  - Spec source: .pennyfarthing/gates/lang-review/python.md, check #3
  - Spec text: "Parameters MUST have type annotations / Return types MUST be annotated"
  - Implementation: `test_is_projectable_has_boundary_type_annotations` uses `inspect.signature` (asserts the param annotation is present and return is `bool`/`"bool"`) rather than `typing.get_type_hints`, so it does not force the `Npc` annotation to resolve at runtime.
  - Rationale: forcing runtime resolution would push Dev to top-level-`import Npc` into `npc_pool.py` → circular import (lang-review #10, since `session.py` already imports `npc_pool.py`). A `TYPE_CHECKING` forward-ref must remain legal. Presence-not-resolution is the correct enforcement.
  - Severity: minor
  - Forward impact: none.

### Dev (implementation)
- No deviations from spec. The predicate implements the ADR-138 §D3 truth table
  exactly as TEA's tests require. Among the two implementations TEA sanctioned
  (getattr duck-typing OR a TYPE_CHECKING forward-ref), I used
  `isinstance(entity, NpcPoolMember)` + an annotation-only `Npc` forward-ref under
  `TYPE_CHECKING` — explicit (reads like the ADR's two cases) and robust even if
  `Npc` ever gained an `observation_pending` field. No runtime `import Npc`, so no
  circular import. This is a choice within TEA's offered menu, not a spec deviation.

### Reviewer (audit)
- **TEA: No production-path wiring test for the predicate** → ✓ ACCEPTED by Reviewer: ADR-138 §Implementation-Stories explicitly scopes 75-11 to "predicate + unit tests … No wiring yet" — story scope is the highest spec authority and overrides the blanket "Every Test Suite Needs a Wiring Test" rule. The consumers (75-12 ADR-118, 75-13 ADR-135) carry the behaviour/OTEL wiring tests. The import/callable reachability test is the correct assertion at this tier. NOT a half-wired-feature violation.
- **TEA: Type-annotation rule (#3) asserted by presence, not runtime resolution** → ✓ ACCEPTED by Reviewer: forcing `get_type_hints` resolution would push Dev to a runtime `import Npc` → circular import (lang-review #10, since `session.py` imports `npc_pool.py`). `inspect.signature` presence-check is the right enforcement; a `TYPE_CHECKING` forward-ref must stay legal. Verified the implementation used exactly this (annotation-only `Npc` under `TYPE_CHECKING`, npc_pool.py:18-23).
- **Dev: isinstance over getattr duck-typing** → ✓ ACCEPTED by Reviewer: within TEA's explicitly-offered menu; `isinstance(entity, NpcPoolMember)` is more robust than `getattr(...,"observation_pending",False)` (survives `Npc` ever gaining the field). `Npc`/`NpcPoolMember` are sibling BaseModels, so the isinstance branch is sound. Not a spec deviation.
- No undocumented deviations found — the implementation matches ADR-138 §D3 and TEA's tests exactly.

## Sm Assessment

Story 75-11 (2pt, p2, tdd) implements ADR-138 §D1/D3: the `is_projectable()`
predicate where `observation_pending` gates whether an entity is eligible for
projection. Setup complete — session + story/epic context written, feature branch
`feat/75-11-is-projectable-observation-pending` created on sidequest-server/develop.

**Routing note for TEA (Igor):** The sprint YAML carried no description/ACs, so ACs
are yours to define in RED. The authoritative spec is **ADR-138 §D1/D3**
(`docs/adr/138-npc-ratification-gates-projection.md`) — read it first. This is
**wiring/integration of an existing concept**, not greenfield: `is_projectable` /
`observation_pending` already appear in `session_helpers.py`, `narration_apply.py`,
`world_materialization.py`, `npc_pool.py`, and `telemetry/spans/npc.py`. Verify
whether the predicate exists vs. needs introduction and that it is reached from a
production path ("Verify Wiring, Not Just Existence"). Per project doctrine the
eligibility decision must emit an OTEL watcher span (GM panel = lie detector); the
RED suite needs a wiring test plus a span-assertion test. See the enriched
`sprint/context/context-story-75-11.md` for file pointers.

Jira: intentionally skipped — SideQuest is a personal project (sprint YAML only).

---
## TEA Assessment

**Tests Required:** Yes
**Reason:** N/A — 75-11 ships a new behavioral predicate.

**Test Files:**
- `sidequest-server/tests/game/test_npc_pool_is_projectable.py` — truth-table +
  rule-enforcement unit tests for `is_projectable()` (ADR-138 §D1/D3). 8 tests.

**Tests Written:** 8 tests covering the ADR-138 §D3 truth table (TEA-authored ACs —
the sprint YAML carried none; derived from ADR-138 §D3 + the 75-11 implementation-
story line).

**Status:** RED (failing — ready for Dev). Verified via testing-runner: the new file
errors at collection with `ImportError: cannot import name 'is_projectable' from
sidequest.game.npc_pool` (canonical RED for a not-yet-existing predicate). Sibling
`tests/game/test_npc_pool_model.py` still passes (19 passed) — no regression.

**Acceptance Criteria (TEA-defined from ADR-138 §D3):**
- AC1 — ratified pool member (`observation_pending=False`) → `is_projectable` True.
- AC2 — pending pool member (`observation_pending=True`) → `is_projectable` False.
- AC3 — default-constructed pool member (defaults ratified) → True.
- AC4 — promoted `Npc` is **always** projectable → True (independent of its own state).
- AC5 — for a pool member, predicate is exactly `not observation_pending` (both branches).
- AC6 — predicate lives beside the model in `npc_pool.py`, importable with no circular
  import (lang-review #10).
- AC7 — predicate has boundary type annotations (lang-review #3).

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #3 type annotations at boundaries | `test_is_projectable_has_boundary_type_annotations` | failing (RED) |
| #6 test quality (meaningful assertions) | self-check — all 8 assert specific values; `is True`/`is False`/`==`, no `assert True`/truthy-only | pass (self) |
| #10 import hygiene (no circular import) | `test_is_projectable_is_importable_and_callable` (module-top import resolves) | failing (RED) |

**Rules checked:** 3 of 13 lang-review rules apply to a pure pydantic predicate +
unit tests (#3 annotations, #6 test-quality, #10 import-hygiene). The other 10
(silent-exceptions, mutable-defaults, logging, path-handling, resource-leaks,
unsafe-deser, async, input-validation, dependency-hygiene, fix-regressions) do not
apply to this change.
**Self-check:** 0 vacuous tests found. Every test asserts a specific boolean value or
the `not observation_pending` identity; no `let _ =`/`assert True`/always-None patterns.

**Note for Dev (Ponder):** This is a *behavioral* predicate — NOT a wiring story.
Do NOT wire `is_projectable` into any consumer (ADR-138: wiring is 75-12/75-13).
Just add the predicate to `npc_pool.py` to turn RED → GREEN. Heed the circular-import
finding above (no top-level `import Npc`).

**Handoff:** To Dev for implementation (GREEN).

---
## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/game/npc_pool.py` — added the `is_projectable()`
  predicate beside `NpcPoolMember` (ADR-138 §D3) + an annotation-only `Npc` import
  under `TYPE_CHECKING`. `isinstance(entity, NpcPoolMember)` → `not observation_pending`;
  promoted `Npc` → always `True`. +30 lines, additive only.

**Tests:** 9/9 passing (GREEN) — `tests/game/test_npc_pool_is_projectable.py`.
Regression: full `tests/game/` suite **2471 passed, 15 skipped, 0 failures** (npc_pool
is widely imported; no breakage). `ruff check` ✓, `ruff format --check` ✓, `pyright`
0 errors on the changed file.

**Branch:** `feat/75-11-is-projectable-observation-pending` (pushed to origin).

**Scope honored:** predicate only — NOT wired into any consumer, per ADR-138 (wiring is
75-12/75-13) and TEA's explicit instruction. No production consumer exists yet by design;
the reachability assertion is the import/callable test.

**Self-review:**
- [x] Follows project patterns (predicate beside model; TYPE_CHECKING forward-ref to
  dodge the known circular import)
- [x] All 7 TEA ACs met (truth table + annotations + import hygiene)
- [x] No error handling needed — pure total boolean function, no I/O, no failure modes
- [x] No OTEL span needed at this tier — §D6 spans belong to the consumers (75-12
  `retrieval.npc_unratified_skipped`, etc.); a pure predicate emits nothing
- [x] Minimalist — no abstraction beyond the two-branch predicate the tests demand

**Handoff:** To Reviewer (Granny Weatherwax) for code review.

---
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (ruff format --check red on test file) | confirmed 1 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (preflight returned; 8 disabled via workflow.reviewer_subagents — I assessed their domains myself below)
**Total findings:** 1 confirmed ([LOW] format), 0 dismissed, 0 deferred

## Rule Compliance

Self-assessed (8 specialist subagents are disabled via settings; I covered their domains):

### lang-review/python.md (the 3 of 13 rules that apply to a pure predicate + tests)
- **#3 type annotations at boundaries** — COMPLIANT. `is_projectable(entity: NpcPoolMember | Npc) -> bool` (npc_pool.py:90). Public boundary fully annotated; return `bool`. The `Npc` half is an annotation-only `TYPE_CHECKING` forward-ref (npc_pool.py:18-23) — correct, avoids the circular import.
- **#6 test quality** — COMPLIANT. All 9 tests assert specific values (`is True`/`is False`/`== (not pending)`); the parametrize covers BOTH branches (distinct code paths, not the same path); no `assert True`, no truthy-only, no skips, no missing assertions. `[TEST]` domain (subagent disabled) — assessed clean by me.
- **#10 import hygiene** — COMPLIANT. No star import; the `Npc` import is `TYPE_CHECKING`-gated precisely BECAUSE a runtime import would be circular (`session.py`→`npc_pool.py`). Module-level test import of `is_projectable` resolves (preflight collection succeeded → no cycle). `__all__` is absent on `npc_pool.py` but was absent before this diff — pre-existing module choice, not introduced here; non-blocking.
- Rules **#1,2,4,5,7,8,9,11,12,13** (silent-exceptions, mutable-defaults, logging, path-handling, resource-leaks, unsafe-deser, async, input-validation, dependency-hygiene, fix-regressions) — N/A: a pure total boolean function with no I/O, no mutable defaults, no exceptions, no external input, no deps changed.

### SOUL.md / CLAUDE.md
- **OTEL Observability** — N/A at this tier. CLAUDE.md exempts cosmetic/no-subsystem-decision code; ADR-138 §D6 places the projection spans on the CONSUMERS (75-12 `retrieval.npc_unratified_skipped`, 75-13). A pure predicate with no production caller emits nothing. `[VERIFIED]` — ADR-138 §D6 assigns spans to fill/index seam, not the predicate.
- **No Silent Fallbacks** — `[VERIFIED]` the else→`True` branch is type-guarded (`NpcPoolMember | Npc` + pyright), not a config/path fallback. npc_pool.py:108-109.

## Observations (≥5)

1. `[VERIFIED]` Predicate logic matches ADR-138 §D3 exactly — `not entity.observation_pending` for a pool member, `True` for an `Npc` — npc_pool.py:107-109 does precisely this. Truth table fully covered by tests.
2. `[VERIFIED]` `isinstance(entity, NpcPoolMember)` is sound — `Npc` (session.py:126) and `NpcPoolMember` (npc_pool.py:27) are SIBLING `BaseModel`s, not parent/child, so an `Npc` correctly falls through to `return True`. No subtype trap.
3. `[VERIFIED]` Circular import avoided — `Npc` is annotation-only under `TYPE_CHECKING` (npc_pool.py:18-23); preflight collected the test (which imports `is_projectable` at module top) with no ImportError → no cycle. pyright clean.
4. `[LOW][preflight]` `ruff format --check` red on `tests/game/test_npc_pool_is_projectable.py` — cosmetic reflow only (collapse multi-line `NpcPoolMember(...)` calls; one docstring `""""Always` → `""" "Always`). No behavioral impact. Production file already formatted. **This is the sole blocking-the-gate item.**
5. `[VERIFIED]` Test quality is high — `is True`/`is False` identity checks (not truthy), parametrize exercises both branches, annotation test uses `inspect.signature` (not `get_type_hints`) to avoid forcing the forward-ref to resolve. No vacuous assertions.
6. `[VERIFIED]` Scope honored — predicate only, no consumer wired (ADR-138: wiring is 75-12/75-13). Not a half-wired feature; TEA/Dev/ADR all corroborate.
7. `[LOW]` `npc_pool.py` has no `__all__` (lang-review #10 mentions it) — but this predates the diff; not introduced here. Non-blocking, out of scope.

### Devil's Advocate

Let me argue this code is broken. First attack: the `return True` fall-through. The predicate trusts that anything which is not an `NpcPoolMember` must be a projectable `Npc`. But Python does not enforce the `NpcPoolMember | Npc` annotation at runtime. If a future caller passes `None`, a `Companion`, a `dict`, or a freshly-renamed model, `is_projectable` returns `True` silently — a phantom could be projected, the exact failure ADR-138 exists to prevent. Counter: at THIS tier there is no caller at all (wiring is 75-12/75-13), and the two future callers are the index/reference projectors which iterate typed `npc_pool: list[NpcPoolMember]` and `npcs: list[Npc]` — both well-typed sources. pyright guards the contract statically. So the risk is theoretical, not present; I record it as [LOW] context for 75-12/75-13, not a block.

Second attack: the truth-table inversion. Could `not entity.observation_pending` be backwards? If a pending (auto-minted, uncommitted) member returned `True`, phantoms would be embedded. The test `test_pending_pool_member_is_not_projectable` pins `observation_pending=True → False`, and the parametrized identity test pins both branches. Inversion is impossible without a red test. Safe.

Third attack: a confused author in 75-12 imports the predicate but forgets the `Npc`-always-True case and only gates pool members, leaking a pending member that was promoted mid-turn. That is a 75-12 concern, and the Dev finding already flags the consumer contract. Not this diff's defect.

Fourth attack: the stressed filesystem / huge input angle — irrelevant; this is a pure in-memory boolean with no I/O, no recursion, no allocation beyond a bool, no timeout surface. There is no failure mode to induce.

The devil finds only the red format gate and a theoretical untyped-input note. Nothing structural.

## Reviewer Assessment

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [LOW] | `ruff format --check` is red — gate failure (cosmetic reflow) | `tests/game/test_npc_pool_is_projectable.py` | Run `uv run ruff format tests/game/test_npc_pool_is_projectable.py`, re-verify GREEN, commit + push |

**Why REJECT on a [LOW]:** The verdict is not about code danger — the logic is correct and the predicate is exemplary. It is about a **red quality gate**. `ruff format --check` fails, and the tdd workflow provides the exact sanctioned edge for lint/format-only findings (review → green rework → Dev). Landing unformatted code when `check-all` does not run `ruff format --check` would let it persist silently. One command fixes it. Granny does RIGHT, not nice.

**Subagent dispatch tags:** `[EDGE]` n/a (disabled — pure total fn, no boundaries beyond the two-branch truth table, covered by me obs. 1-2), `[SILENT]` n/a (disabled — no exceptions/fallbacks, obs. assessed in Rule Compliance), `[TEST]` clean (disabled — assessed by me, obs. 5), `[DOC]` clean (disabled — docstring accurate; the `""""Always` nit is the format reflow, obs. 4), `[TYPE]` clean (disabled — obs. 2/3, sibling-model isinstance sound), `[SEC]` n/a (disabled — no input boundary, no secrets, no injection surface), `[SIMPLE]` clean (disabled — minimal two-branch predicate, no over-engineering), `[RULE]` see Rule Compliance (disabled — #3/#6/#10 compliant, format gate red).

**Data flow traced:** `entity: NpcPoolMember | Npc` → `isinstance` branch → `not observation_pending` (pool member) or `True` (Npc) → bool. No mutation, no I/O, total function. Safe.

**Handoff:** Back to Dev (Ponder Stibbons) for the format fix (green rework).

---
## Dev Assessment — Rework R1 (format)

**Fix applied:** `uv run ruff format tests/game/test_npc_pool_is_projectable.py` — the
sole [LOW] finding from Granny's review. Cosmetic reflow only (collapsed multi-line
`NpcPoolMember(...)` calls; one docstring whitespace nit). No production code touched;
`npc_pool.py` was already formatted.

**Re-verification (GREEN):** 9/9 tests pass. `ruff format --check` now clean on **both**
changed files (prod + test — closing Granny's process Improvement finding). `ruff check`
all passed. Committed `e3699ac3`, pushed.

**No new deviations.** A whitespace reflow is not a spec deviation; the predicate logic
is unchanged from the approved-logic review.

**Handoff:** To Reviewer (Granny Weatherwax) to confirm the format gate is green.

---
## Subagent Results (Review Round 2 — confirmation)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (9/9 GREEN, format ✓, check ✓) | confirmed 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (preflight clean; 8 disabled via settings; this is a format-only confirmation round)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

## Reviewer Assessment (Round 2)

**Verdict:** APPROVED

**Confirmation basis:** The sole prior finding ([LOW] red `ruff format --check` on the
test file) is resolved. Verified `git diff 11af2771 HEAD -- sidequest/game/npc_pool.py`
is **empty** — the predicate source is byte-identical to what I logic-approved last
round; only test-file whitespace moved (5 ins / 13 del, line collapses). `ruff format
--check` now reports both files already formatted; `ruff check` passes; preflight 9/9
GREEN; no smells.

**Subagent dispatch tags:** `[EDGE]` n/a (disabled — confirmed clean R1, pure total fn), `[SILENT]` n/a (disabled — no exceptions/fallbacks), `[TEST]` clean (disabled — 9/9, both branches pinned), `[DOC]` clean (disabled — the docstring `""""Always` nit was the format reflow, now fixed), `[TYPE]` clean (disabled — sibling-model isinstance sound, unchanged), `[SEC]` n/a (disabled — no input boundary), `[SIMPLE]` clean (disabled — minimal two-branch predicate), `[RULE]` clean (disabled — #3/#6/#10 compliant; format gate now GREEN).

**Data flow traced:** unchanged from Round 1 — `entity: NpcPoolMember | Npc` → `isinstance`
branch → `not observation_pending` (pool member) or `True` (Npc) → bool. Total function,
no I/O, safe.

**Pattern observed:** predicate beside the model with a `TYPE_CHECKING` forward-ref to
dodge the `session.py`→`npc_pool.py` cycle — `sidequest/game/npc_pool.py:90`. Correct.

**Error handling:** N/A — pure total boolean, no failure modes (verified R1).

**Deviations:** all three logged deviations stamped ✓ ACCEPTED (see Reviewer audit). No
undocumented deviations.

**Handoff:** To SM (Captain Carrot) for finish-story.