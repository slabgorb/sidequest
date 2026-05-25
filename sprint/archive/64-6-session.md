---
story_id: "64-6"
jira_key: "64-6"
epic: "64"
workflow: "tdd"
---
# Story 64-6: Fix circular import — WebSocketSessionHandler back-compat re-export cycle

## Story Details
- **ID:** 64-6
- **Epic:** 64 (Content Schema Compliance — Close Pack Validator Gaps)
- **Jira Key:** 64-6
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** sidequest-server

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-25T12:26:43Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-25T00:00:00Z | 2026-05-25T11:56:56Z | 11h 56m |
| red | 2026-05-25T11:56:56Z | 2026-05-25T11:59:25Z | 2m 29s |
| green | 2026-05-25T11:59:25Z | 2026-05-25T12:16:59Z | 17m 34s |
| spec-check | 2026-05-25T12:16:59Z | 2026-05-25T12:17:53Z | 54s |
| verify | 2026-05-25T12:17:53Z | 2026-05-25T12:21:54Z | 4m 1s |
| review | 2026-05-25T12:21:54Z | 2026-05-25T12:25:44Z | 3m 50s |
| spec-reconcile | 2026-05-25T12:25:44Z | 2026-05-25T12:26:43Z | 59s |
| finish | 2026-05-25T12:26:43Z | - | - |

## Story Context

Pre-existing circular import surfaced during epic 64 review: 

```
tests/dungeon/test_region_projection_wiring.py::test_dungeon_map_frame_is_emitted_to_ui
```

Fails in isolation with: `cannot import name WebSocketSessionHandler from partially initialized module sidequest.server.websocket_session_handler`

**The cycle:**
- `session_handler.py:640` re-exports `WebSocketSessionHandler` from `websocket_session_handler.py` (back-compat)
- `websocket_session_handler.py:144` imports `_SessionData`/`_State`/etc back from `session_handler.py`

Importing either module first in a fresh interpreter can hit the half-initialized partner.

**Solution approach:** Break the cycle by either:
1. Moving shared types to a leaf module (no circular dependencies)
2. Dropping the back-compat re-export if unused

## Acceptance Criteria
- [ ] `test_region_projection_wiring.py::test_dungeon_map_frame_is_emitted_to_ui` passes when run in isolation
- [ ] No import cycle between `session_handler` and `websocket_session_handler` (verified by importing each first in a fresh interpreter)
- [ ] Full dungeon suite green; no regression in server suite

## Sm Assessment

Setup complete. Scope is a well-isolated pre-existing circular import between `session_handler.py` (line 640 back-compat re-export) and `websocket_session_handler.py` (line 144 type imports), surfaced during epic 64 review. Self-contained server-only fix; no cross-repo coordination needed.

**Branch topology note for implementers:** the working branch `feat/64-6-fix-import-cycle` exists on BOTH the orchestrator (off `main`) and the `sidequest-server` subrepo (off `develop`). All implementation commits land on the server subrepo branch — it was created explicitly because sm-setup only branched the orchestrator.

**Watch item:** AC says "break the cycle by moving shared types to a leaf module OR dropping the back-compat re-export if unused" — the re-export at `session_handler.py:640` should be checked for live consumers before deletion (grep for `from sidequest.server.session_handler import WebSocketSessionHandler`). If consumers exist, prefer the leaf-module extraction. The fix blocks 64-4 (validator imports the loader graph that transitively pulls these modules), so it's load-bearing for the rest of epic 64.

## Delivery Findings

No upstream findings.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (blocking): The `WebSocketSessionHandler` re-export at `session_handler.py:640` has ~50 live importers — production (`sidequest/server/app.py`, `websocket.py`, `emitters.py`, `views.py`, `dispatch/lore_embed.py`) plus ~45 test modules — so the context's "drop the re-export if unused" option is NOT viable. Affects `sidequest/server/session_handler.py:640` (keep the re-export; break the cycle via the leaf-extraction approach instead — relocate `_SessionData`, `_State`, `_build_pc_descriptor`, `_hash_snapshot`, `_shared_world_delta_to_state_delta`, `_AUDIO_INTERPRETER` to a leaf module both handlers import). *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): The server suite carries **21 pre-existing failures unrelated to 64-6** — `test_61_12_output_format_compaction` (8), `test_wire_parity` (5), `test_audit_namegen_corpora` (4), and one each in `test_prompt_cache_attribution_otel`, `test_dogfight_playtest_smoke`, `test_character_sheet_abilities`, `test_turn_status_roster`. Proven independent of this change: none of these test files reference `session_handler`/`session_state`/`websocket_session_handler` at runtime, and a `comm` diff of pre- vs post-fix runs shows zero new regressions. Affects multiple unrelated subsystems (prompt output-format, wire serialization, namegen corpus audit) — should be triaged separately by their owners. *Found by Dev during implementation.*

### TEA (test verification)
- **Improvement** (non-blocking): `_presence_msg` is defined identically in both `sidequest/server/websocket.py` (~line 219) and `sidequest/server/session_helpers.py` (~line 1258); the session_helpers copy is the canonical one re-exported via `session_handler.__all__`. Affects `sidequest/server/websocket.py` (delete the local copy, import `_presence_msg` from `session_helpers`). Pre-existing, unrelated to the 64-6 import-cycle fix — surfaced by the verify simplify pass, deferred as out-of-scope cleanup. *Found by TEA during test verification.*

### Reviewer (code review)
- No upstream findings. The change is a clean, byte-identical structural relocation; both enabled specialists (preflight, security) returned clean, and independent review confirmed no behavior, type, wire, or trust-boundary change. (The pre-existing `_presence_msg` duplication TEA logged remains the only out-of-scope cleanup item.)

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- **Updated one pre-existing audio-dispatch test's patch target**
  - Spec source: context-story-64-6.md, Scope Boundaries ("Update any import sites touched by relocating the shared symbols")
  - Spec text: "Update any import sites touched by relocating the shared symbols."
  - Implementation: `tests/server/test_audio_dispatch.py::test_maybe_dispatch_audio_swallows_exceptions_from_interpreter` patched `session_handler.AudioInterpreter`; since `_AUDIO_INTERPRETER` (and the `AudioInterpreter` import behind it) moved to the `session_state` leaf, the patch target was changed to the canonical `sidequest.audio.interpreter.AudioInterpreter.interpret`.
  - Rationale: `AudioInterpreter` (the class) was never part of `session_handler`'s intended public API — only the `WebSocketSessionHandler` + underscore helpers were. Repointing to the canonical class is more refactor-stable than re-exporting an incidental implementation import. Verified no other consumer reached `session_handler.AudioInterpreter`.
  - Severity: minor
  - Forward impact: none

### Reviewer (audit)
- **TEA (test design): "No deviations from spec."** → ✓ ACCEPTED by Reviewer: confirmed — the RED tests are pure AC2 coverage with no spec divergence.
- **Dev (implementation): audio-dispatch test patch-target update (`session_handler.AudioInterpreter` → canonical `sidequest.audio.interpreter.AudioInterpreter.interpret`)** → ✓ ACCEPTED by Reviewer: sound (Option A). `AudioInterpreter` the class was never part of `session_handler`'s intended API — only `WebSocketSessionHandler` + underscore helpers were. The class relocated with `_AUDIO_INTERPRETER` to the leaf; patching the canonical class is more refactor-stable than re-exporting an incidental import, and since `patch` targets a class method it correctly affects the shared singleton. No other consumer reached `session_handler.AudioInterpreter` (verified). No undocumented deviations found by Reviewer.

### Architect (reconcile)

Verified the in-flight deviation log against the spec sources (context-story-64-6.md, context-epic-64.md):

- **TEA "No deviations from spec."** — accurate. The RED tests cover AC2 with no divergence.
- **Dev "audio-dispatch test patch-target update"** — all 6 fields present and accurate. Spec text "Update any import sites touched by relocating the shared symbols." verified verbatim at context-story-64-6.md:58 (Scope Boundaries → In scope). Implementation and forward-impact (none) confirmed against the diff.

One deviation TEA/Dev did not log, added here for a complete manifest:

- **Incidental ruff-format reformat of unrelated code in `session_helpers.py`**
  - Spec source: context-story-64-6.md, Scope Boundaries
  - Spec text: "Broader server import-graph cleanup beyond what this one cycle requires." (listed under **Out of scope**)
  - Implementation: Running `ruff format` on `session_helpers.py` after the in-scope `TYPE_CHECKING` import repoint also reflowed a pre-existing `routes_list.append({...})` call in `_build_cartography_map_message` (diff lines ~379-396) from a single-arg-dict style to the formatter's canonical multi-line style. This reflow is unrelated to the import-cycle fix.
  - Rationale: Formatter output, not a hand edit — `ruff format` normalizes the whole file, and this block had drifted from canonical style. Reverting it would leave the file non-canonical and re-dirty on the next format run. Behavior is byte-identical (pure whitespace).
  - Severity: trivial
  - Forward impact: none — pure whitespace, no semantic or wire change.


## TEA Assessment

### Red Phase (test writing)

**Tests Required:** Yes
**Reason:** AC2 requires a structural import-order check; no existing test covers it.

**Test Files:**
- `tests/server/test_session_handler_import_cycle.py` — fresh-interpreter import-order regression guard for the `session_handler` ↔ `websocket_session_handler` cycle.

**Tests Written:** 3 tests covering AC2 (1 parametrized over both cycle modules = 2 cases + 1 combined order-independence test).
**Status:** RED (2 failing, 1 passing — ready for Dev)

- `test_module_imports_first_in_fresh_interpreter[websocket_session_handler]` → **FAIL** (`ImportError: cannot import name 'WebSocketSessionHandler' from partially initialized module`)
- `test_both_cycle_modules_import_regardless_of_order` → **FAIL** (names `websocket_session_handler` as the failing first-import)
- `test_module_imports_first_in_fresh_interpreter[session_handler]` → PASS (symmetric guard; this order already works — kept as a regression sentinel)

The two failures are the meaningful RED. The one pass is intentional: it locks in the import order that currently works so a future refactor can't silently flip the cycle the other way.

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| No source-text wiring tests (CLAUDE.md) | uses subprocess fresh-interpreter import (runtime check), NOT `read_text()`/grep — explicitly permitted | satisfied |
| Every test asserts something meaningful (TEA) | both tests assert `returncode == 0` + absence of "partially initialized module" in stderr | satisfied |
| No vacuous assertions (TEA self-check) | no `let _ =` / `assert True` / always-None asserts present | satisfied |

**Rules checked:** Python repo — no `lang-review/python.md` numbered checklist applies to a pure import-graph refactor; the applicable rules are CLAUDE.md's "No Source-Text Wiring Tests" (honored via subprocess import check) and TEA's meaningful-assertion rule.
**Self-check:** 0 vacuous tests found.

**Handoff:** To Dev for implementation (leaf-extraction — see blocking Delivery Finding).
## Dev Assessment

**Implementation Complete:** Yes
**Approach:** Leaf-module extraction (as TEA's blocking finding mandated — the re-export has ~50 importers so "drop it" was off the table).

**Files Changed:**
- `sidequest/server/session_state.py` (NEW) — leaf module holding `_SessionData`, `_State`, `_hash_snapshot`, `_shared_world_delta_to_state_delta`, `_AUDIO_INTERPRETER`, `_build_pc_descriptor`. Imports only modules that don't import back into the cycle (`session_helpers`' sole `session_handler` import is `TYPE_CHECKING`-guarded).
- `sidequest/server/session_handler.py` — removed the six definitions + their now-orphaned imports; re-imports all six from the leaf (`# noqa: F401` back-compat re-export) so every existing `from session_handler import ...` call site still resolves; removed the emptied `if TYPE_CHECKING: pass` scaffold.
- `sidequest/server/websocket_session_handler.py` — line-144 import repointed from `session_handler` → `session_state` (the edge that severs the cycle).
- `sidequest/server/session_helpers.py` — `TYPE_CHECKING` import of `_SessionData` repointed to the leaf.
- `tests/server/test_audio_dispatch.py` — one patch target updated (see deviation).

**Tests:** GREEN.
- New `tests/server/test_session_handler_import_cycle.py`: 3/3 pass (both import orders + order-independence).
- AC1 `test_dungeon_map_frame_is_emitted_to_ui` passes in isolation.
- AC3 dungeon suite: 458 passed. Server suite: 7953 passed / 21 failed — the 21 are **pre-existing and unrelated** (proven by zero coupling + zero new regressions in a pre/post `comm` diff). The 4 failures this change initially introduced (back-compat re-export gaps surfaced by ruff's unused-import autofix) were caught and fixed before commit.

**Branch:** `feat/64-6-fix-import-cycle` (pushed, tracking origin).

**Handoff:** To TEA (Radar) for the verify phase.
## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

All three ACs map cleanly to the implementation, and the approach is the exact one the story context prescribed:

- **AC1** (dungeon test passes in isolation) — Dev confirms PASS; the structural fix removes the ImportError root cause.
- **AC2** (no cycle, both orders succeed) — verified independently: `session_state.py` imports neither `session_handler` nor `websocket_session_handler` (true leaf), and `websocket_session_handler` now imports the six shared symbols from the leaf rather than from `session_handler` — the cycle edge is severed, not merely reordered. The 3 new fresh-interpreter tests lock this in.
- **AC3** (dungeon suite green, no regression) — dungeon suite 458 green; the 21 server-suite failures are pre-existing and proven uncoupled to the four touched modules.

**Design quality notes (within standard):**
- Leaf-extraction was the correct call over the context's alternate "drop the re-export" option — TEA's ~50-importer finding made deletion untenable. The diamond is now a tree.
- The back-compat re-export from `session_handler` (`# noqa: F401`) preserves the full public import surface, so none of the ~50 call sites churn. This is the right restraint — no gratuitous import-site rewrites.
- The one deviation (audio-dispatch test patch target) is well-reasoned and falls under Option A (code/test reveals the cleaner canonical target); repointing to `sidequest.audio.interpreter.AudioInterpreter` is more refactor-stable than re-exporting an incidental class import. Accepted as logged.

**Decision:** Proceed to review (verify phase).
## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5 (4 changed source + new test)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 2 findings | 1 high (out of scope), 1 low (no action) |
| simplify-quality | 2 findings | 1 medium (declined), 1 low (noted) |
| simplify-efficiency | clean | — |

**Applied:** 0 fixes
**Flagged for Review:** 0
**Noted/Declined:** 4

Triage detail:
- **reuse `_presence_msg` duplicated in `websocket.py:219` (high):** NOT in this story's diff. `websocket.py` is untouched by 64-6; the verify simplify pass scopes to changed files, and editing an unrelated module would expand the diff with no relation to the import-cycle fix. **Out of scope** — surfaced as a non-blocking Delivery Finding for separate cleanup.
- **quality `__all__` re-export inconsistency, `session_handler.py:42` (medium):** Declined. The four helpers (`_AUDIO_INTERPRETER`, `_build_pc_descriptor`, `_hash_snapshot`, `_shared_world_delta_to_state_delta`) were **never in `__all__` before this story** — they were importable module internals. The re-import faithfully preserves that exact prior surface. Trimming them risks breaking unfound `patch()`/attribute consumers (exactly the failure mode caught during green: `test_audio_dispatch` reached `session_handler.AudioInterpreter` via attribute access, invisible to import-grep). Preserving the full importable surface is the correct back-compat choice; `_shared_world_delta_to_state_delta` has a confirmed external importer (`tests/magic/test_delta.py`).
- **reuse leaf cross-call (low) / quality `__all__` comment accuracy (low):** noted, no action — cosmetic, and the comment predates this story.

### Regression Detection

No simplify changes applied → no revert risk. Re-verified post-analysis: changed files lint-clean (ruff), and a stability spot-check of the new import-cycle tests + the four green-phase fixes + AC1 dungeon test = 13/13 pass.

**Quality Checks:** ruff clean on all changed files; GREEN stable.
**Handoff:** To Reviewer (Colonel Potter) for code review.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 smells; tests GREEN 461/0; both import orders PASS; lint clean | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — reviewer assessed boundary paths directly (see [EDGE]) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — reviewer assessed directly (see [SILENT]) |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings — reviewer assessed test quality directly (see [TEST]) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — reviewer assessed docs directly (see [DOC]) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — reviewer assessed types directly (see [TYPE]) |
| 7 | reviewer-security | Yes | clean | 0 findings; projection byte-identical, no injection surface | N/A |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — reviewer assessed complexity directly (see [SIMPLE]); also covered by TEA verify simplify pass |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — reviewer enumerated rules directly (see Rule Compliance + [RULE]) |

**All received:** Yes (2 enabled returned: preflight + security; 7 disabled via `workflow.reviewer_subagents`)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred (both enabled specialists clean)

## Reviewer Assessment

**Verdict:** APPROVED

This is a textbook structural refactor: six symbols relocated from `session_handler.py` to a new leaf module `session_state.py` to sever a real import cycle, with back-compat re-exports preserving the entire prior import surface. I read the full 864-line diff line-by-line and confirmed the relocation is **byte-identical** — every docstring, comment, field, and the `_shared_world_delta_to_state_delta` projection body matches the deleted original character-for-character. No logic changed; only location.

### Observations

1. **[VERIFIED] Byte-identical relocation** — the six definitions in `session_state.py:456-725` match the deletions from `session_handler.py` exactly (diff lines 75-359 deleted ≡ 456-725 added). No transformation slipped in during the move. Complies with the "no behavior change" scope boundary in context-story-64-6.md.
2. **[VERIFIED] The leaf is genuinely a leaf** — `session_state.py` imports neither `session_handler` nor `websocket_session_handler`; its only server-internal runtime imports are `session_helpers._resolve_acting_character_name` and `image_pacing.ImagePacingThrottle`, both confirmed not to import back (session_helpers' `_SessionData` import is `TYPE_CHECKING`-guarded, diff line 372-375). The diamond is now a tree.
3. **[VERIFIED] Cycle edge severed, not reordered** — `websocket_session_handler.py` no longer imports from `session_handler` at all (diff 734-741 deleted); it pulls the six from `session_state` (749-756). Both fresh-interpreter import orders PASS (preflight). The new test locks this in permanently.
4. **[VERIFIED] Back-compat surface preserved** — `session_handler.py:59` re-exports all six (`# noqa: F401`); re-export is by identity (`from session_state import ...`), so `isinstance` checks and the ~50 `from session_handler import _SessionData/_State/WebSocketSessionHandler` call sites keep working unchanged.
5. **[VERIFIED] `__module__` relocation is inert** — `_SessionData.__module__` is now `session_state`, but nothing pickles `_SessionData` (grep: zero `pickle.dump/load` in `sidequest/`) and nothing keys off its `__module__`. Save files use `snapshot_json`, not pickled session state. No silent breakage.
6. **[SEC]** reviewer-security: clean. Wire projection (`_shared_world_delta_to_state_delta`) byte-identical → ADR-104/105 canonical/perceived split (characters/quests/items_gained default None by construction) is preserved. Test subprocess uses static list-form `subprocess.run` — no shell, no interpolation, no injection surface.
7. **[EDGE]** (disabled — assessed directly): The only branching logic moved is `_build_pc_descriptor`'s two None-returns (empty `snapshot.characters`; no matching character). Both are documented intentional signals, unchanged by the move. No new boundary paths introduced.
8. **[SILENT]** (disabled — assessed directly): No swallowed errors introduced. `_build_pc_descriptor` returning `None` is the documented "catalog-miss → daemon prose-subject prompt" contract (explicitly "not a silent fallback" per its docstring), preserved verbatim. No new try/except.
9. **[TEST]** (disabled — assessed directly): `test_session_handler_import_cycle.py` is high quality — fresh-interpreter subprocess (the only correct way to test import-order independence), meaningful assertions (`returncode == 0` AND absence of "partially initialized module" so a different crash can't masquerade as pass), parametrized over both modules + a combined order-independence case. No vacuous assertions. The `session_handler`-first case intentionally passes as a regression sentinel.
10. **[DOC]** (disabled — assessed directly): `session_state.py`'s module docstring documents the "must stay a leaf" invariant and *why* `session_helpers` is safe (TYPE_CHECKING-guarded) — exactly the kind of non-obvious constraint that warrants a comment. The `# noqa: F401` comment accurately states the re-export rationale. No stale/misleading docs.
11. **[TYPE]** (disabled — assessed directly): No type contracts changed. `_SessionData` fields, `_State` enum members, and all signatures are identical post-move. No stringly-typed APIs or unsafe casts introduced.
12. **[SIMPLE]** (disabled — assessed directly; corroborated by TEA's verify simplify pass which ran reuse/quality/efficiency): No over-engineering. The leaf module is the minimal vehicle to break the cycle. The one medium finding from verify (re-exports not in `__all__`) was correctly declined as a preserved pre-existing condition.
13. **[RULE]** (disabled — assessed directly, see Rule Compliance below): All applicable project rules pass.

### Rule Compliance

| Rule (source) | Instances checked | Verdict |
|---------------|-------------------|---------|
| No Source-Text Wiring Tests (server CLAUDE.md) | New test file | COMPLIANT — uses subprocess **runtime** import, not `read_text()`/grep; explicitly the blessed exception |
| No Silent Fallbacks (CLAUDE.md/SOUL) | `_build_pc_descriptor` None-returns, no new fallbacks | COMPLIANT — documented correct signals, byte-identical |
| No Stubbing (CLAUDE.md) | New leaf module | COMPLIANT — real relocated code, no shells |
| Wire Up What Exists / Verify Wiring (CLAUDE.md) | Cycle fix | COMPLIANT — reuses existing modules; non-test consumer (`websocket_session_handler`) imports the leaf |
| Every Test Suite Needs a Wiring Test (CLAUDE.md) | Import-cycle suite | COMPLIANT — the test verifies real cross-module importability end-to-end |
| Perception split ADR-104/105 (memory) | `_shared_world_delta_to_state_delta` | COMPLIANT — perceived fields None by construction, unchanged (security-confirmed) |
| Genre models extra=forbid (memory) | — | N/A — no model/YAML schema fields touched |

### Devil's Advocate

Let me argue this is broken. **First attack — the leaf isn't actually a leaf.** `session_state.py` imports `session_helpers` at runtime, and `session_helpers` is a sprawling module; if *any* runtime import in `session_helpers`' transitive closure reaches back to `session_handler` or `session_state`, the cycle just moved rather than broke. Rebuttal: both fresh-interpreter import orders pass in a clean process (preflight + the new test), which exercises the *entire* transitive closure — a latent cycle would surface as exactly the `ImportError` the test guards against. Empirically refuted.

**Second attack — the re-export is a lie.** If `session_handler` re-exports `_SessionData` but some consumer does `isinstance(x, session_handler._SessionData)` while the object was constructed referencing `session_state._SessionData`, identity could diverge. Rebuttal: the re-export is `from session_state import _SessionData` — the *same* class object, one identity. `isinstance` is safe.

**Third attack — module-level side effects double-fire.** `_AUDIO_INTERPRETER = AudioInterpreter()` now lives in `session_state`, imported by *two* modules; could it instantiate twice? Rebuttal: Python caches modules in `sys.modules`; the module body runs once regardless of how many importers. Single singleton, same as before.

**Fourth attack — a confused maintainer deletes the "unused" re-exports.** ruff flagged the four helpers as unused-by-session_handler; a future cleanup pass could drop them and silently break `tests/magic/test_delta.py` (imports `_shared_world_delta_to_state_delta` from `session_handler`) or a `patch()` target. This is a *real* latent fragility — but it's mitigated by the explicit `# noqa: F401 — back-compat re-export ... consumed by external importers + mock.patch targets` comment, which tells the maintainer exactly why they exist. Acceptable with the comment as the guardrail.

**Fifth attack — a stressed filesystem / weird save.** Irrelevant: this diff touches no I/O, no persistence, no parsing. The save path is untouched.

Devil's advocate uncovers no new blocking finding. The fourth point is already captured as a deliberate design choice with a protective comment.

**Data flow traced:** `SharedWorldDelta` → `_shared_world_delta_to_state_delta` (now in `session_state`, byte-identical) → wire `StateDelta` with perceived fields None → unchanged from pre-refactor. Safe.
**Pattern observed:** Clean leaf-extraction to break an import diamond — `session_state.py:1-46`.
**Error handling:** No error paths changed; `_build_pc_descriptor` None-signals preserved verbatim.

**Handoff:** To SM (Hawkeye) for finish-story.