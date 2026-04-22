---
story_id: "37-48"
jira_key: ""
epic: "SQ-37"
workflow: "trivial"
---

# Story 37-48: Test-lock run_narration_turn builds TurnContext with npc_registry

## Story Details

- **ID:** 37-48
- **Jira Key:** (pending)
- **Epic:** SQ-37 — Playtest 2 Fixes — Multi-Session Isolation
- **Workflow:** trivial (stepped: setup → implement → review → finish)
- **Points:** 1
- **Type:** chore (test-locking)
- **Stack Parent:** none
- **Repos:** sidequest-server

## Summary

Follow-up from story 37-44 reviewer round-2. Add test in `tests/server/test_npc_identity_drift.py` that locks `orchestrator.py:1324` so a future refactor cannot silently drop the `npc_registry=` kwarg without CI catching it.

**No production code changes.** This is purely a test-locking story.

**MUST land before playtest 4.**

## Acceptance Criteria

1. **Test location:** `tests/server/test_npc_identity_drift.py`

2. **Test function:** `test_run_narration_turn_passes_npc_registry_to_turn_context`

3. **Implementation approach:**
   - Monkeypatch `sidequest.agents.orchestrator.Orchestrator.run_narration_turn` to capture the `context` argument
   - Invoke the module-level function with a seeded `session.npc_registry` 
   - Assert `captured_context.npc_registry == session.npc_registry`

4. **Guard purpose:** Lock in the call at `orchestrator.py:1324` so that if a future refactor removes the `npc_registry=` kwarg, the test will fail and CI will catch it

5. **Context from review round-2:** 
   - Round-1 reviewer marked severity as HIGH
   - Round-2 accepted as a test-locking gap (not a behavioral gap)
   - The additive-only guard at `session_handler.py:1623-1631` already protects the story-goal invariant
   - This test closes the gap

## Key References

- **Story 37-44:** NPC identity drift detection and remediation
- **Orchestrator call:** `orchestrator.py:1324` (the `run_narration_turn` call that must preserve `npc_registry=`)
- **Guard logic:** `session_handler.py:1623-1631` (additive-only protection)
- **Test suite:** `tests/server/test_npc_identity_drift.py`

## Workflow Tracking

**Workflow:** trivial (stepped)  
**Phase:** finish  
**Phase Started:** 2026-04-22T20:18:27Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-22T19:16:51Z | — | — |

## SM Assessment

**Scope is tight and well-bounded.** This is a 1-point test-locking chore with a precise target:
- Single test function in `tests/server/test_npc_identity_drift.py`
- Monkeypatch-and-capture pattern verifying `orchestrator.py:1324` passes `npc_registry=` kwarg
- Zero production code changes

**Priority justification:** Flagged MUST-LAND-BEFORE-PLAYTEST-4 by round-2 reviewer on 37-44. Closes the test-locking gap that let round-1 severity HIGH downgrade to round-2 accepted. Without it, a future refactor can silently drop the kwarg and CI won't notice.

**Handoff to Dev (Agent Smith):** Implementation approach is fully specified in Acceptance Criteria. The Merovingian will review after. No design ambiguity — proceed to implement.

## Delivery Findings

No upstream findings.

## Design Deviations

### Dev (implementation)
- No deviations from spec.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-server/tests/server/test_npc_identity_drift.py` — Added `test_run_narration_turn_passes_npc_registry_to_turn_context` (72 new lines). Monkeypatches `Orchestrator.run_narration_turn` to capture the TurnContext argument, invokes the module-level `sidequest.agents.orchestrator.run_narration_turn` with a seeded `session.npc_registry` (canonical Frandrew entry), asserts `captured_context.npc_registry == session.npc_registry`. Locks `orchestrator.py:1324` so a future refactor cannot silently drop the `npc_registry=` kwarg.

**Tests:** 20/20 passing in `tests/server/test_npc_identity_drift.py` (GREEN). New test runs in < 0.1s.

**Branch:** `feat/37-48-test-lock-run-narration-turn-npc-registry` pushed to origin on both orchestrator and sidequest-server.

**Production code changes:** None. Pure test-locking story as specified.

**Branch note for Reviewer:** sidequest-server branch is stacked on top of `feat/37-44-npc-identity-drift` (37-44 has not yet landed on main). The new test depends on 37-44 code (NpcRegistryEntry, `_apply_narration_result_to_snapshot`, `session.npc_registry`). Pre-existing uncommitted multiplayer WIP in `rest.py`, `session_handler.py`, and `spans.py` was preserved in the working tree — not included in this commit.

**Handoff:** To Review phase (Reviewer / The Merovingian).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 2 ruff (F401, I001) | confirmed 0, dismissed 2 (pre-existing), deferred 0 |
| 2 | reviewer-edge-hunter | Yes | findings | 5 | confirmed 0, dismissed 5, deferred 0 |
| 3 | reviewer-silent-failure-hunter | Yes | clean | none | N/A |
| 4 | reviewer-test-analyzer | Yes | clean | none | N/A |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 | confirmed 2, dismissed 0, deferred 0 |
| 6 | reviewer-type-design | Yes | clean | none | N/A |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | Yes | clean | none | N/A |
| 9 | reviewer-rule-checker | Yes | findings | 1 | confirmed 0, dismissed 1, deferred 0 |

**All received:** Yes (9 returned, 4 with findings)
**Total findings:** 2 confirmed, 8 dismissed (with rationale), 0 deferred

### Dismissal rationale

- **[EDGE] missing `@pytest.mark.asyncio`** — dismissed: `asyncio_mode = "auto"` is set in `sidequest-server/pyproject.toml:36`. Config drift would be caught at suite level.
- **[EDGE] wrapper exception masking** — dismissed: the "wrapper short-circuited" assertion message is best-effort context, not a contract. An actual exception surfaces as pytest error with full traceback — strictly more informative than the fallback message.
- **[EDGE] identity vs equality semantic gap** — dismissed: story AC asks for equality, not identity. Production does `list(session.npc_registry)` — copy semantics are intentional. Locking identity would be brittle.
- **[EDGE] npcs/npc_registry swap gap** — dismissed: author-noted, covered by non-empty registry fixture.
- **[EDGE] fake_method signature resilience** — dismissed: the point of the lock is to couple to the current signature. `**kwargs` would defeat the guard.
- **[RULE] missing type annotations on test function** — dismissed (low severity): pytest test functions are not boundary-consumed public APIs and the project does not enforce annotations on tests elsewhere in the same file. `monkeypatch: pytest.MonkeyPatch` would be fine but isn't required.
- **[PREFLIGHT] F401 `pytest` imported but unused (line 30)** — dismissed: pre-existing on `feat/37-44-npc-identity-drift`, not introduced by this diff. Out of scope for 37-48. File should be cleaned in a follow-up chore.
- **[PREFLIGHT] I001 import sort** — dismissed: pre-existing. Same as above.

## Rule Compliance

Checked `.pennyfarthing/gates/lang-review/python.md` + `CLAUDE.md` principles against the 72-line diff.

| Rule | Instances in diff | Compliant | Notes |
|------|-------------------|-----------|-------|
| Silent exception swallowing | 0 | — | No try/except in diff. |
| Mutable default arguments | 2 fn defs | ✓ | None. |
| Type annotation gaps at boundaries | 2 fn defs | partial | Test fn missing annotations; dismissed (see above). |
| Logging coverage | 0 | — | No logging touched. |
| Path handling | 0 | — | No filesystem. |
| Test quality (vacuous assertions, mock target) | 2 assertions, 1 monkeypatch | ✓ | Both assertions carry diagnostic messages; monkeypatch targets `orch_module.Orchestrator` — correct target where the wrapper resolves the attribute. |
| Resource leaks | 0 | — | No resources opened. |
| Unsafe deserialization | 0 | — | None. |
| Async/await pitfalls | 2 async defs, 1 await | ✓ | `asyncio_mode = "auto"` covers unmarked `async def`. Coroutine awaited. |
| Import hygiene | 1 runtime import | ✓ | `from sidequest.agents import orchestrator as orch_module` inside function is intentional (explicit late-binding for monkeypatch target). |
| Security input validation | 0 | — | Test file, no input surface. |
| No silent fallbacks (CLAUDE.md) | 1 | ✓ | First assertion fails loudly if wrapper short-circuits. |
| No stubbing (CLAUDE.md) | 1 | ✓ | `fake_method` is a monkeypatch shim, not a placeholder module. |
| Verify wiring, not just existence (CLAUDE.md) | 1 | ✓ | This IS the wiring test for the `npc_registry → TurnContext` path. |
| OTEL Observability Principle (CLAUDE.md) | — | N/A | No subsystem fix. Rule does not apply to pure test additions. |

## Devil's Advocate

*This code is broken. Let me prove it.* The test claims to lock `orchestrator.py:1324`, but the header comment and the assertion failure message both hardcode the number 1324. Orchestrator.py is 1329 lines long and growing — any insertion above line 1324 silently invalidates both references. When the test fails in 2027 after three unrelated refactors, the on-call engineer will jump to `orchestrator.py:1324` and land on a comment or blank line, wasting fifteen minutes before realizing the pointer rotted. This is exactly the "documentation that rots faster than the code it describes" antipattern CLAUDE.md warns about. **Real finding, already flagged by `[DOC]`.**

What about the monkeypatch itself? `monkeypatch.setattr(orch_module.Orchestrator, "run_narration_turn", fake_method)` replaces the method on the *class* — pytest-monkeypatch restores it on teardown via fixture scope. But if any concurrent test in the same event loop happens to invoke `Orchestrator.run_narration_turn` during this test's window, it gets the fake. Pytest-asyncio default-scope is function-level, so this is safe under current config, but if `asyncio_mode` ever shifts to session scope, concurrent runs could cross-contaminate. Low-probability regression in a future config change — not a current bug.

Could a malicious payload break this test? The test constructs all inputs locally — no user input surface. No.

What about filesystem drift? The test creates no files, reads no config, spawns no subprocess. Hermetic.

What happens if `NpcRegistryEntry` changes shape? If someone adds a required field without defaults, the `NpcRegistryEntry(name="Frandrew", role="captain", pronouns="she/her", last_seen_turn=17)` construction raises at collection time — TypeError, loud and obvious. Not silent.

What if `list(session.npc_registry)` in production starts deep-copying? Pydantic `__eq__` is by-value — the assertion still passes. The test cannot distinguish shallow from deep copy. This is a *semantic weakness* but not a bug: the invariant the test locks is "registry content reaches the context," and that holds for both copies.

One last stone to kick: the test file has `import pytest` at line 30 that ruff flags as unused (F401). Inherited from 37-44. If dev had run `ruff check --fix` on this branch before committing, it would have been removed — and the `@pytest.mark.asyncio` defensive decorator that edge-hunter wanted would have re-introduced the import. A small irony, but it tells me the file isn't under active ruff gating. Not this story's fault; worth a follow-up chore.

Verdict holds. The code does what it says. The only real wart is the rotting line number in comments, and that is a LOW-severity doc finding, not a regression risk.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:**
- Test seeds `GameSnapshot(npc_registry=[Frandrew])` → monkeypatches `Orchestrator.run_narration_turn` to capture context → awaits module-level `orch_module.run_narration_turn(...)` wrapper → wrapper at `sidequest-server/sidequest/agents/orchestrator.py:1291-1329` builds TurnContext via `npc_registry=list(session.npc_registry)` (line 1324) → captured context's `npc_registry` is asserted equal to seeded list.
- Production wiring verified at `orchestrator.py:1324`:
  ```python
  context = TurnContext(
      ...
      npc_registry=list(session.npc_registry),
      ...
  )
  ```
- Test fails loudly if a future refactor drops the kwarg (TurnContext default is `field(default_factory=list)` → `[] != [NpcRegistryEntry(...)]`).

**Pattern observed:** Monkeypatch-capture for wrapper wiring verification — `tests/server/test_npc_identity_drift.py:700-709`. Correct pytest idiom. Couples intentionally to the wrapper→method delegation, which is the invariant being locked.

**Error handling:** Test's first assertion (`"context" in captured`) is a loud-fail precondition check against wrapper short-circuit — `test_npc_identity_drift.py:716`. Satisfies CLAUDE.md "No Silent Fallbacks."

**Wiring verified:** This test IS the wiring check for `GameSnapshot.npc_registry → TurnContext.npc_registry`. Module-level `run_narration_turn` is exercised end-to-end; `Orchestrator.run_narration_turn` is the delegation target being locked. Satisfies CLAUDE.md "Every Test Suite Needs a Wiring Test."

**Subagent coverage:**
- `[EDGE]` — 5 findings, all dismissed with rationale above
- `[SILENT]` — clean
- `[TEST]` — clean (auto-mode asyncio verified; assertions non-vacuous; no implementation-coupling violation)
- `[DOC]` — 2 confirmed (see observations below)
- `[TYPE]` — clean (Pydantic `__eq__`, dataclass `TurnContext` equality both verified)
- `[SEC]` — clean (test-only, no threat surface)
- `[SIMPLE]` — clean (every element load-bearing)
- `[RULE]` — 1 dismissed (test fn type annotations; project convention exempts)

**Observations (non-blocking, all LOW):**

| Severity | Issue | Location | Note |
|----------|-------|----------|------|
| `[LOW] [DOC]` | Hardcoded line number `orchestrator.py:1324` in section header comment will rot as orchestrator.py grows | `tests/server/test_npc_identity_drift.py:658` | Function name (`run_narration_turn`) is stable; line number is not. Recommend stripping the `:1324` in a follow-up. Not blocking — incident-grade institutional memory in the docstring itself is intact. |
| `[LOW] [DOC]` | Same hardcoded line number in assertion failure message; wording in past tense ("refactored away") is slightly confusing for a future-regression guard | `tests/server/test_npc_identity_drift.py:721-724` | When the test fails, the failure message points to a possibly-stale line. Function name + explanation would be enough. Not blocking. |
| `[LOW] [PREFLIGHT]` | `import pytest` unused (F401), import sort (I001) | `tests/server/test_npc_identity_drift.py:26,30` | **Pre-existing** on parent branch, not introduced by this diff. Flag for a follow-up lint-sweep chore. Ruff auto-fixable. Out of scope for 37-48. |

**[VERIFIED]** Test assertion fails if `npc_registry=list(session.npc_registry)` is dropped from `orchestrator.py:1324` — `TurnContext.npc_registry` default is `field(default_factory=list)` (line 311), so removal yields empty list, assertion compares `[] == [NpcRegistryEntry(...)]`, fails. Confirmed by test-analyzer against line-311 default.

**[VERIFIED]** No production code changes — `git show --stat 850e4d3` reports `1 file changed, 72 insertions(+)`; the only file touched is `tests/server/test_npc_identity_drift.py`. Story AC #1-4 satisfied.

**[VERIFIED]** `asyncio_mode = "auto"` in `sidequest-server/pyproject.toml:36` — bare `async def` test collects and runs under pytest-asyncio without explicit decorator. Complies with Python async/await rule.

**[VERIFIED]** Monkeypatch target correctness — `orch_module.Orchestrator.run_narration_turn` is the attribute resolved by the module-level wrapper at `orchestrator.py:1328-1329`. Patching here intercepts the delegation, which is precisely the wire being locked.

**Handoff:** To SM (Morpheus) for finish-story.

## Delivery Findings

### Reviewer (code review)
- **Improvement** (non-blocking): Comments and assertion failure message at `tests/server/test_npc_identity_drift.py:658` and `:721-724` hardcode `orchestrator.py:1324`. Function names are stable, line numbers drift. Recommend a trivial follow-up PR to replace `:1324` references with function-name references. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Pre-existing ruff F401/I001 on `tests/server/test_npc_identity_drift.py:26,30` (inherited from feat/37-44-npc-identity-drift — `import pytest` unused, import sort). Ruff `--fix` resolves both. Worth bundling into the lint-sweep chore. *Found by Reviewer during code review.*

---

**Branch:** `feat/37-48-test-lock-run-narration-turn-npc-registry`  
**Session Created:** 2026-04-22T19:16:51Z  
**Next Agent:** sm (finish phase)