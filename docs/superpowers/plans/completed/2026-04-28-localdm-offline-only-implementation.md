# LocalDM Offline-Only Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take the LocalDM Haiku decomposer off the live turn critical path so the narrator's Opus subprocess is the only LLM call required before NARRATION emission. Eliminate ~5–10s per solo and MP turn.

**Architecture:** The narrator prompt currently consumes a `DispatchPackage` produced by LocalDM. After this change, `TurnContext.dispatch_package` is always `None` on the live turn; `build_narrator_prompt` already has `is None` guards at the three consumption sites and uses default zones only. The dispatch bank, prompt redaction, and Group G visibility infrastructure stay on disk as **dormant** code (clearly marked, ready to re-engage when ADR-073's local fast router lands). Training-corpus capture is unchanged: the existing SQLite save already records `PLAYER_ACTION` events and narration; `sidequest/corpus/miner.py` extracts JSONL on demand.

**Tech Stack:** Python 3.12, asyncio, pydantic v2, FastAPI, pytest, pytest-asyncio, uv.

**Spec:** `docs/superpowers/specs/2026-04-28-localdm-offline-only-design.md`

**Working dir:** `/Users/slabgorb/Projects/oq-2/sidequest-server` for all server tasks. Project root `/Users/slabgorb/Projects/oq-2` for cross-cutting items (docs, justfile).

---

## File Map

| File | Change |
|---|---|
| `sidequest/server/websocket_session_handler.py` | Remove LocalDM call (~lines 1187-1229), set `visibility_sidecar=None`, remove `secret_routes` reify loop |
| `sidequest/server/session_handler.py` | Remove `local_dm: LocalDM = field(default_factory=LocalDM)` from `_SessionData` |
| `sidequest/agents/orchestrator.py` | Verify `is None` guards at lines 871, 1355, 1561; nothing should change if guards are complete |
| `sidequest/agents/local_dm.py` | Add DORMANT marker at top of file |
| `sidequest/agents/prompt_redaction.py` | Add DORMANT marker at top of file |
| `sidequest/agents/subsystems/__init__.py` | Add DORMANT marker at top of file |
| `sidequest/agents/subsystems/distinctive_detail.py` | Add DORMANT marker at top of file |
| `sidequest/agents/subsystems/npc_agency.py` | Add DORMANT marker at top of file |
| `sidequest/agents/subsystems/reflect_absence.py` | Add DORMANT marker at top of file |
| `tests/agents/test_orchestrator.py` (new test) | Unit test: `build_narrator_prompt` with `dispatch_package=None` skips redaction + bank |
| `tests/server/test_session_handler_localdm_offline.py` (new file) | Wiring test: turn completes when `LocalDM.decompose` raises |
| `tests/corpus/test_miner_post_localdm_offline.py` (new file) | Miner produces TrainingPair rows from a post-change save |

---

## Task 1: Verify orchestrator dispatch_package guards

**Files:**
- Read-only: `sidequest/agents/orchestrator.py`

- [ ] **Step 1: Audit all readers of `context.dispatch_package`**

Run from `sidequest-server/`:
```bash
grep -n "dispatch_package" sidequest/agents/orchestrator.py
```

Expected hits at minimum (line numbers approximate, verify in current file):
- `438`: field definition `dispatch_package: DispatchPackage | None = None` — already optional
- `744`: comment about `redact_dispatch_package`
- `871-880`: `if context.dispatch_package is not None:` → calls `redact_dispatch_package`
- `1355`: `if visible_dispatch_package is not None:` → runs dispatch bank + lethality arbiter
- `1561`: `if context.dispatch_package is not None:` → calls `audit_canonical_prose`

- [ ] **Step 2: Confirm every read is guarded**

Read each match. For any read site not inside an `if … is not None:` branch, make a note. If all reads are already guarded, this task is verification-only — no edit.

If any read is unguarded, that's a bug to fix in this task with a guard. Likely zero unguarded reads given the existing Group G work, but verify, don't assume.

- [ ] **Step 3: No commit needed if no edits made**

If edits were required, commit with:
```bash
git add sidequest/agents/orchestrator.py
git commit -m "fix(orchestrator): guard dispatch_package read at <line>"
```

---

## Task 2: Unit test — build_narrator_prompt with None dispatch_package

**Files:**
- Modify: `tests/agents/test_orchestrator.py`

- [ ] **Step 1: Find the existing pattern for orchestrator unit tests**

Run:
```bash
grep -n "async def test_\|def make_orchestrator\|def make_turn_context" tests/agents/test_orchestrator.py | head -20
```

Note the helpers used by existing `build_narrator_prompt` tests. Reuse them — do not duplicate fixture builders.

- [ ] **Step 2: Add the failing test**

Append to `tests/agents/test_orchestrator.py`:

```python
async def test_build_narrator_prompt_with_none_dispatch_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When TurnContext.dispatch_package is None, build_narrator_prompt
    must skip redact_dispatch_package, skip dispatch-bank execution,
    and produce a prompt without subsystem-injected sections."""
    orchestrator = make_orchestrator()  # reuse existing helper
    ctx = make_turn_context(dispatch_package=None)  # extend helper if needed

    redact_called = False
    bank_called = False

    def _fake_redact(*args, **kwargs):  # pragma: no cover — must NOT be called
        nonlocal redact_called
        redact_called = True
        raise AssertionError("redact_dispatch_package called on None path")

    async def _fake_bank(*args, **kwargs):  # pragma: no cover — must NOT be called
        nonlocal bank_called
        bank_called = True
        raise AssertionError("run_dispatch_bank called on None path")

    monkeypatch.setattr(
        "sidequest.agents.prompt_redaction.redact_dispatch_package", _fake_redact
    )
    monkeypatch.setattr(
        "sidequest.agents.subsystems.run_dispatch_bank", _fake_bank
    )

    prompt_text, _registry = await orchestrator.build_narrator_prompt(
        action="I look around.",
        context=ctx,
        tier=NarratorPromptTier.Full,
    )

    assert redact_called is False
    assert bank_called is False
    assert prompt_text  # prompt was built successfully
```

If `make_turn_context` does not accept a `dispatch_package` kwarg or does not default it to `None`, extend the helper. Do NOT inline a TurnContext constructor — keep helpers DRY.

- [ ] **Step 3: Run the test (expect pass — guards already exist)**

Run:
```bash
uv run pytest tests/agents/test_orchestrator.py::test_build_narrator_prompt_with_none_dispatch_package -v
```

Expected: PASS. Task 1 verified the guards. This test pins the behavior so a future patch that removes a guard fails loudly.

If the test FAILS, investigate which guard is missing in the orchestrator code and fix in this task before committing. The test going green is a precondition for Task 3.

- [ ] **Step 4: Commit**

```bash
git add tests/agents/test_orchestrator.py
git commit -m "test(orchestrator): pin None-dispatch-package code path

The redact + dispatch-bank skips are already in place via is-None
guards. This test pins the behavior so future regressions surface
instead of silently re-engaging dormant code.
"
```

---

## Task 3: Wiring test — turn completes when LocalDM.decompose raises

**Files:**
- Create: `tests/server/test_session_handler_localdm_offline.py`

- [ ] **Step 1: Find an existing session-handler integration test to model on**

Run:
```bash
grep -rln "_execute_narration_turn\|websocket_session_handler" tests/server/ tests/integration/ | head -10
```

Open the first hit and note: how is a test session built? How is a fake narrator wired? What pytest fixtures are reused?

The wiring-test pattern usually involves: a pre-built `_SessionData`, a recorded narrator that returns canned output, and a fake genre pack. Reuse these helpers.

- [ ] **Step 2: Write the failing test**

Create `tests/server/test_session_handler_localdm_offline.py`:

```python
"""Wiring test: LocalDM is no longer on the live turn path.

If a future change re-introduces ``await sd.local_dm.decompose(...)`` on
the critical path, this test fails loud. The dormant code in
``sidequest/agents/local_dm.py`` MUST NOT be invoked during a live turn.
"""
from __future__ import annotations

import pytest

from sidequest.agents.local_dm import LocalDM


@pytest.mark.asyncio
async def test_live_turn_does_not_invoke_local_dm(
    monkeypatch: pytest.MonkeyPatch,
    # reuse the project's standard session-handler fixture; substitute the
    # real fixture name found in Step 1 (e.g., `running_session`,
    # `playing_session_data`, etc.)
    playing_session_data,
) -> None:
    """Patch LocalDM.decompose to raise. Run a turn. Assert it succeeds."""
    def _explode(*args, **kwargs):
        raise AssertionError("LocalDM.decompose was called on the live turn")

    async def _async_explode(*args, **kwargs):
        _explode()

    # LocalDM.decompose is async — patch with an async raiser. Cover the
    # sync path too in case a refactor flips it.
    monkeypatch.setattr(LocalDM, "decompose", _async_explode)

    sd, handler, action_msg = playing_session_data
    result = await handler.handle_message(action_msg)

    # Turn completed without invoking LocalDM. Frames returned.
    assert result, "turn handler returned no frames"
```

If the project has no `playing_session_data`-style fixture, copy the setup from the integration test you opened in Step 1. Do not invent a new fixture in this file — promote one to `conftest.py` if needed.

- [ ] **Step 3: Run the test (expect fail BEFORE Task 4 lands)**

Run:
```bash
uv run pytest tests/server/test_session_handler_localdm_offline.py -v
```

Expected: FAIL with `AssertionError: LocalDM.decompose was called on the live turn`. This confirms the test catches the regression we're about to fix.

- [ ] **Step 4: Commit the failing test**

```bash
git add tests/server/test_session_handler_localdm_offline.py
git commit -m "test(session_handler): pin LocalDM off the live turn path (RED)

Failing test before the implementation lands — Task 4 makes it pass by
removing the LocalDM call from _execute_narration_turn.
"
```

---

## Task 4: Remove LocalDM call from _execute_narration_turn

**Files:**
- Modify: `sidequest/server/websocket_session_handler.py:1187-1229`

- [ ] **Step 1: Read the current LocalDM block in context**

Run:
```bash
sed -n '1180,1235p' sidequest/server/websocket_session_handler.py
```

Confirm the block looks like:
```python
turn_id = (
    f"{sd.genre_slug}:{sd.world_slug}:{sd.player_id}:"
    f"{snapshot.turn_manager.interaction}"
)
assert turn_context.state_summary is not None, (
    "TurnContext.state_summary must be populated by _build_turn_context"
)
with timings.phase("preprocess_llm"):
    dispatch_package = await sd.local_dm.decompose(
        turn_id=turn_id,
        player_id=f"player:{sd.player_name}",
        raw_action=action,
        state_summary=turn_context.state_summary,
        visibility_baseline=sd.genre_pack.visibility_baseline,
    )
if dispatch_package.degraded:
    logger.info(
        "session.decomposer_degraded reason=%s turn_id=%s",
        dispatch_package.degraded_reason,
        turn_id,
    )
    _watcher_publish(
        "decomposer_degraded",
        {
            "turn_id": turn_id,
            "reason": dispatch_package.degraded_reason or "",
            "player_id": f"player:{sd.player_name}",
        },
        component="local_dm",
        severity="warning",
    )
turn_context.dispatch_package = dispatch_package
```

- [ ] **Step 2: Replace the entire block with a single comment**

Edit `sidequest/server/websocket_session_handler.py`. Replace lines 1187-1229 (the `# Group B — Local DM decomposer …` comment through `turn_context.dispatch_package = dispatch_package`) with:

```python
# LocalDM is dormant on the live turn path as of 2026-04-28
# (docs/superpowers/specs/2026-04-28-localdm-offline-only-design.md).
# turn_context.dispatch_package stays None; build_narrator_prompt's
# is-None guards skip redaction and the dispatch bank.
```

The `turn_id` local variable was only used inside the LocalDM block — also remove it. The `assert turn_context.state_summary is not None` was a precondition for LocalDM — also remove it (the narrator does not require state_summary the same way).

If `turn_id` or `state_summary` is referenced later in the same function, leave whichever lines are still needed and only remove the LocalDM-specific ones. Use grep within the function to verify.

- [ ] **Step 3: Run the wiring test from Task 3 (expect PASS)**

Run:
```bash
uv run pytest tests/server/test_session_handler_localdm_offline.py -v
```

Expected: PASS.

- [ ] **Step 4: Run the broader test suite to surface regressions**

Run:
```bash
uv run pytest -x --tb=short
```

Expect failures in tests that asserted on `dispatch_package` content — those are addressed in Task 5 and Task 7. Note the failing test names. Do NOT fix them in this task; fix them in their dedicated tasks. If a failure is unrelated to dispatch_package or LocalDM, stop and investigate before continuing.

- [ ] **Step 5: Commit**

```bash
git add sidequest/server/websocket_session_handler.py
git commit -m "refactor(session_handler): remove LocalDM decompose from live turn

The narrator's Opus subprocess is now the only LLM call on the critical
path. turn_context.dispatch_package stays None; build_narrator_prompt's
is-None guards already skip redaction and the dispatch bank.

Wiring test test_live_turn_does_not_invoke_local_dm now passes.
Some existing tests that pinned dispatch-package content are expected
to fail — those are repaired in subsequent tasks.
"
```

---

## Task 5: Set visibility_sidecar to None in NarrationPayload

**Files:**
- Modify: `sidequest/server/websocket_session_handler.py:1410-1415`

- [ ] **Step 1: Read the current NarrationPayload construction**

Run:
```bash
sed -n '1405,1420p' sidequest/server/websocket_session_handler.py
```

Confirm the call:
```python
narration_payload = NarrationPayload(
    text=narration_nbs,
    state_delta=None,
    footnotes=forwarded_footnotes,
    visibility_sidecar=aggregate_visibility(dispatch_package),
)
```

After Task 4 removed the LocalDM block, `dispatch_package` is no longer defined as a local. This line currently produces a `NameError` at runtime — the implementation is broken between Task 4 and Task 5. Acceptable: Task 4's commit is fine because the wiring test mocks LocalDM and never hits the broadcast path; the broader test suite caught this in Task 4 Step 4.

- [ ] **Step 2: Replace the call with `visibility_sidecar=None`**

Edit the construction:
```python
narration_payload = NarrationPayload(
    text=narration_nbs,
    state_delta=None,
    footnotes=forwarded_footnotes,
    # visibility_sidecar stays None on the live turn — the dispatch
    # package that fed aggregate_visibility(...) is dormant. MP wiring
    # will reintroduce a visibility classifier; until then, peers see
    # the same canonical narration.
    visibility_sidecar=None,
)
```

If `aggregate_visibility` is no longer imported anywhere, also remove its import from the file's imports block. Use grep:
```bash
grep -n "aggregate_visibility" sidequest/server/websocket_session_handler.py
```
If only the import line remains, delete it.

- [ ] **Step 3: Run the wiring test plus a broader sweep**

Run:
```bash
uv run pytest tests/server/test_session_handler_localdm_offline.py -v
uv run pytest tests/integration/test_group_g_e2e.py -v
```

The Group G end-to-end test will likely fail — Group G visibility redaction is exactly the dormant code we just disconnected. Note the failure shape; fix in Task 7.

- [ ] **Step 4: Commit**

```bash
git add sidequest/server/websocket_session_handler.py
git commit -m "refactor(session_handler): visibility_sidecar=None on live turn

dispatch_package is no longer constructed on the live path; the
aggregate_visibility(dispatch_package) call would NameError. Set the
field to None unconditionally — peers see canonical narration. MP
wiring will reintroduce a visibility classifier per the spec.
"
```

---

## Task 6: Remove secret_routes reification on the live turn

**Files:**
- Modify: `sidequest/server/websocket_session_handler.py:1439-1465`

- [ ] **Step 1: Read the current block**

Run:
```bash
sed -n '1438,1470p' sidequest/server/websocket_session_handler.py
```

Confirm the block:
```python
# Group G Task 6: route prompt-redacted dispatches as SECRET_NOTE
# events. Task 5's ``redact_dispatch_package`` stripped these from the
# narrator prompt and parked them on ``result.secret_routes``; here we
# reify each one as its own event so the same ProjectionFilter /
# visibility_tag rule (Task 3) delivers it only to the recipients in
# its ``_visibility.visible_to``. Only SubsystemDispatch entries route;
# see ``build_secret_note_events`` for the skip rules.
for _envelope in build_secret_note_events(
    result.secret_routes,
    ...
):
    ...
```

After Task 4, LocalDM never runs and `redact_dispatch_package` is never called, so `result.secret_routes` is always empty. The loop is a no-op but still imports `build_secret_note_events`.

- [ ] **Step 2: Decide: skip the loop or guard it**

Two options. Pick one:

**Option A (preferred):** Wrap the entire block in `if result.secret_routes:`. The body is dead code today but stays callable when ADR-073 lands and dispatch packages return to the live path. Lowest blast radius.

```python
if result.secret_routes:
    for _envelope in build_secret_note_events(
        result.secret_routes,
        ...
    ):
        ...
```

**Option B:** Delete the block entirely and remove `build_secret_note_events` import. Cleaner, but the dormant routing code in `prompt_redaction.py` no longer has a live caller — making it harder to revive ADR-073 cleanly.

Choose **Option A**. Apply the edit.

- [ ] **Step 3: Run integration tests**

Run:
```bash
uv run pytest tests/integration/test_group_g_e2e.py -v
```

The e2e test will likely still fail — Group G's whole story assumes LocalDM runs. That's expected and addressed in Task 7. Note the failure for Task 7 reference.

- [ ] **Step 4: Run the broader suite to confirm no NEW failures from this edit**

```bash
uv run pytest -x --tb=short -k "not test_group_g"
```

Expected: only the failures already seen in Task 4 Step 4 — no new ones introduced by Tasks 5/6.

- [ ] **Step 5: Commit**

```bash
git add sidequest/server/websocket_session_handler.py
git commit -m "refactor(session_handler): guard secret_routes reify on dormant path

result.secret_routes is empty when LocalDM is dormant. Wrap the
build_secret_note_events loop in an explicit truthiness check so the
dormant code path stays callable when ADR-073 wakes up but the loop
short-circuits on the live turn.
"
```

---

## Task 7: Update or quarantine existing tests that pinned dispatch_package content

**Files:**
- Modify: tests in `tests/agents/test_local_dm*.py`, `tests/agents/test_prompt_redaction.py`, `tests/integration/test_group_g_e2e.py`, `tests/integration/test_group_c_*.py`, anywhere else flagged by Task 4 Step 4.

- [ ] **Step 1: Reproduce the full failure list**

Run:
```bash
uv run pytest -x --tb=short 2>&1 | tee /tmp/localdm-offline-test-fallout.txt
grep "FAILED" /tmp/localdm-offline-test-fallout.txt
```

Capture the exact list. There are three categories:

1. **Direct LocalDM unit tests** (`test_local_dm.py`, `test_local_dm_visibility.py`): these test the dormant module directly. They should still pass — `LocalDM` exists and works, just isn't called from session_handler. If they fail, the failure is unrelated to this story.
2. **Tests that build a `TurnContext` with a populated `dispatch_package`** and assert downstream behavior (orchestrator dispatch-bank, redaction, audit_canonical_prose): these are testing the dormant path. They should still pass — the orchestrator code is unchanged. If they fail, see whether the test is asserting on a `_SessionData.local_dm` field that Task 8 removes.
3. **Integration tests that drive a full turn through the session handler and expect SECRET_NOTE / Group G visibility** (`test_group_g_e2e.py`): these tests are testing the integration we just severed. They will fail because LocalDM no longer runs.

- [ ] **Step 2: Categorize each failure**

For each failed test, label it:
- **A: Unrelated regression** — fix the root cause; do not paper over.
- **B: Dormant-path test** — should still pass against unchanged orchestrator/local_dm code; if it doesn't, fix in this task.
- **C: Integration severed** — quarantine.

- [ ] **Step 3: Quarantine category-C tests**

For each category-C integration test, add a skip marker citing the spec:

```python
@pytest.mark.skip(
    reason=(
        "LocalDM dormant on live turn as of 2026-04-28 "
        "(docs/superpowers/specs/2026-04-28-localdm-offline-only-design.md). "
        "Re-enable when ADR-073 wakes the dispatch bank back up."
    )
)
async def test_group_g_secret_note_routing_e2e(...):
    ...
```

Do NOT delete the test bodies — they encode the contract for ADR-073's eventual re-engagement.

- [ ] **Step 4: Fix any category-B failures by inspection**

For each category-B test that genuinely still depends on the live integration: rewrite to call `LocalDM.decompose` directly (testing the dormant module in isolation) rather than going through the session handler.

- [ ] **Step 5: Run the full suite — green**

```bash
uv run pytest --tb=short
```

Expected: all pass or skipped. Skipped count includes the new dormant quarantines from Step 3.

- [ ] **Step 6: Commit**

```bash
git add tests/
git commit -m "test: quarantine Group G integration tests; verify dormant unit tests

Group G end-to-end tests asserted full LocalDM->dispatch-bank->
redaction->secret-note flow on the live turn. With LocalDM dormant
those tests cannot pass without re-enabling the dispatch package
construction. Quarantined with @pytest.mark.skip citing the spec.

Dormant unit tests in tests/agents/test_local_dm*.py and
test_prompt_redaction.py continue to run — they test the modules
directly without the session-handler integration.
"
```

---

## Task 8: Remove LocalDM from _SessionData

**Files:**
- Modify: `sidequest/server/session_handler.py:543-547`

- [ ] **Step 1: Confirm `sd.local_dm` has no remaining live readers**

Run:
```bash
grep -rn "sd\.local_dm\|self\.local_dm\|\.local_dm\." sidequest/ --include="*.py"
```

Expected: zero hits in `sidequest/` after Task 4. Hits are acceptable in `tests/agents/test_local_dm*.py` because those instantiate `LocalDM()` directly (not via `_SessionData`).

If non-test hits remain, fix them in this task before removing the field.

- [ ] **Step 2: Remove the field and its import**

Edit `sidequest/server/session_handler.py`:

Remove these lines (~543-547):
```python
# Group B Local DM decomposer (Task 10). One instance per session so
# the decomposer can maintain a persistent Haiku sub-session across
# turns. Constructed with a default factory so existing _SessionData
# construction sites require no change.
local_dm: LocalDM = field(default_factory=LocalDM)
```

Remove the `from sidequest.agents.local_dm import LocalDM` import line near the top of the file.

- [ ] **Step 3: Run the suite**

```bash
uv run pytest --tb=short
```

Expected: all pass / skipped. If anything fails citing `local_dm` attribute, return to Step 1 — there's a missed reader.

- [ ] **Step 4: Commit**

```bash
git add sidequest/server/session_handler.py
git commit -m "refactor(session_handler): drop local_dm field from _SessionData

LocalDM has zero live readers after the live-turn path stopped calling
it. The dormant module is still importable directly for unit tests and
the future offline runner.
"
```

---

## Task 9: Add DORMANT marker to local_dm.py

**Files:**
- Modify: `sidequest/agents/local_dm.py`

- [ ] **Step 1: Read the current docstring**

Run:
```bash
sed -n '1,30p' sidequest/agents/local_dm.py
```

The file already starts with a module docstring. Replace it (do NOT prepend a second one).

- [ ] **Step 2: Replace the docstring with the DORMANT marker**

Edit `sidequest/agents/local_dm.py`. Replace the existing module docstring (the triple-quoted block at the very top of the file, before any imports) with:

```python
"""local_dm — DORMANT.

This module is not invoked on the live turn path as of 2026-04-28
(see docs/superpowers/specs/2026-04-28-localdm-offline-only-design.md).

It is preserved for two consumers:
  1. The offline LocalDM corpus runner (follow-up story).
  2. Re-engagement on the live path once ADR-073's local fine-tuned
     router replaces the Haiku CLI subprocess.

Unit tests for this module remain in `just check-all` so it does not
bit-rot. If you find yourself adding a live caller, you are landing
ADR-073 (or undoing this design); update both ends.

Original design: docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md
"""
```

The original docstring's structured-output description is information that the spec already covers — fine to drop.

- [ ] **Step 3: Run the unit tests for the dormant module**

```bash
uv run pytest tests/agents/test_local_dm.py tests/agents/test_local_dm_visibility.py -v
```

Expected: pass. Docstring change is a no-op for behavior.

- [ ] **Step 4: Commit**

```bash
git add sidequest/agents/local_dm.py
git commit -m "docs(local_dm): mark module DORMANT per offline-only spec"
```

---

## Task 10: Add DORMANT marker to prompt_redaction and subsystems

**Files:**
- Modify: `sidequest/agents/prompt_redaction.py`
- Modify: `sidequest/agents/subsystems/__init__.py`
- Modify: `sidequest/agents/subsystems/distinctive_detail.py`
- Modify: `sidequest/agents/subsystems/npc_agency.py`
- Modify: `sidequest/agents/subsystems/reflect_absence.py`

- [ ] **Step 1: For each file, replace the module docstring with the DORMANT marker**

Use this template, substituting `<filename>` for each file's basename:

```python
"""<filename> — DORMANT.

This module is not invoked on the live turn path as of 2026-04-28
(see docs/superpowers/specs/2026-04-28-localdm-offline-only-design.md).

It is preserved for two consumers:
  1. The offline LocalDM corpus runner (follow-up story).
  2. Re-engagement on the live path once ADR-073's local fine-tuned
     router replaces the Haiku CLI subprocess.

Unit tests for this module remain in `just check-all` so it does not
bit-rot. If you find yourself adding a live caller, you are landing
ADR-073 (or undoing this design); update both ends.
"""
```

Apply to all five files. Where a file has no existing module docstring, insert this block as the first lines of the file (before imports).

- [ ] **Step 2: Run the unit tests for each marked module**

```bash
uv run pytest tests/agents/test_prompt_redaction.py tests/agents/test_subsystem_registry.py -v
```

Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add sidequest/agents/prompt_redaction.py sidequest/agents/subsystems/
git commit -m "docs(agents): mark prompt_redaction and subsystems DORMANT

Five modules carry the DORMANT marker block per the localdm-offline-only
spec. Unit tests still run; they will be re-engaged when ADR-073 lands.
"
```

---

## Task 11: Miner verification test

**Files:**
- Create: `tests/corpus/test_miner_post_localdm_offline.py`

- [ ] **Step 1: Find the existing miner test for fixture pattern**

Run:
```bash
ls tests/corpus/
cat tests/corpus/test_going_forward.py | head -60
```

Note the pattern: how is a test save built? Is there a fixture, a fixture-builder, or is a real save mocked from in-memory rows?

- [ ] **Step 2: Write the test**

Create `tests/corpus/test_miner_post_localdm_offline.py`:

```python
"""Miner verification: with LocalDM dormant on the live turn, the
existing corpus miner must still produce TrainingPair rows from a save.

The save's events table records PLAYER_ACTION payloads; narrative_log
records narration. miner.mine_save aligns them by round_number and
emits TrainingPair rows. This test confirms the post-LocalDM-offline
behavior — i.e., that nothing about taking LocalDM off the live path
broke the offline training-corpus extraction.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.corpus.miner import mine_save  # or the actual public entry point
from sidequest.corpus.save_reader import SaveReader
from sidequest.corpus.schema import TrainingPair


@pytest.mark.asyncio
async def test_miner_extracts_action_and_narration_from_post_change_save(
    # Reuse whatever fixture builds a multi-turn session save. Substitute
    # the project's actual fixture name (e.g., `seeded_session_save`,
    # `played_session_db`, etc.) — find it in Step 1.
    multi_turn_save: Path,
) -> None:
    """Run miner against a save produced by the post-LocalDM-offline
    code path. Assert it emits one TrainingPair per played turn with
    non-empty input_text (action) and output_text (narration)."""
    pairs: list[TrainingPair] = list(mine_save(multi_turn_save))

    assert pairs, "miner produced zero pairs — saves no longer capture turns"

    for pair in pairs:
        assert pair.input_text.strip(), (
            f"pair at round {pair.round_number} has empty input_text"
        )
        assert pair.output_text.strip(), (
            f"pair at round {pair.round_number} has empty output_text"
        )
        assert pair.genre, "pair missing genre slug"
        assert pair.world, "pair missing world slug"
```

If `mine_save` is not the actual function name, find it via:
```bash
grep -n "^def \|^async def " sidequest/corpus/miner.py
```
and substitute. If no fixture builds a multi-turn save, write the smallest one in `conftest.py`:

```python
@pytest.fixture
def multi_turn_save(tmp_path: Path, ...) -> Path:
    """Builds a save with 3 PLAYER_ACTION events + 3 narrative_log rows."""
    # Implementation defers to existing test helpers — see how
    # tests/server/* construct an in-memory SqliteStore.
    ...
```

- [ ] **Step 3: Run the test (expect pass)**

```bash
uv run pytest tests/corpus/test_miner_post_localdm_offline.py -v
```

Expected: PASS. The miner is unchanged code; this test pins success criterion #3 (corpus extractable from post-change saves).

If FAIL because a field on TrainingPair is empty in this code path, that's a real find — the miner needs extending. Fix the miner in this task before committing.

- [ ] **Step 4: Commit**

```bash
git add tests/corpus/test_miner_post_localdm_offline.py
git commit -m "test(corpus): pin miner output against post-LocalDM-offline saves

Confirms the existing corpus miner produces non-empty TrainingPair
rows from a save written by the new live-turn path. Locks success
criterion #3 of the localdm-offline-only spec.
"
```

---

## Task 12: Latency benchmark scenario

**Files:**
- Create: `scenarios/localdm-offline-latency.yaml`
- Create or modify: `scripts/playtest/measure_turn_latency.py` (only if no equivalent exists)

- [ ] **Step 1: Inspect existing scenarios and playtest scripts**

Run:
```bash
ls scenarios/
ls scripts/
grep -rn "phase_durations_ms\|preprocess_llm" scripts/ scenarios/ 2>/dev/null | head
```

If a turn-latency measurement script already exists, modify it. If not, create one.

- [ ] **Step 2: Create the scenario**

Create `scenarios/localdm-offline-latency.yaml`:

```yaml
# Latency benchmark for the localdm-offline-only spec.
#
# Drives ~10 solo turns end-to-end against a running server using a
# recorded narrator stub (deterministic Opus latency). Captures
# phase_durations_ms from each TurnRecord. Asserts:
#   1. preprocess_llm phase is absent or zero on every turn.
#   2. median total_ms is at least 5000ms below a captured baseline.
#
# Run via:
#   just playtest-scenario localdm-offline-latency
#
# Baseline (pre-change) — capture with:
#   git checkout HEAD~10 -- sidequest/server/websocket_session_handler.py
#   just playtest-scenario localdm-offline-latency --record-baseline
#   git checkout HEAD -- sidequest/server/websocket_session_handler.py

name: localdm-offline-latency
genre: caverns_and_claudes
world: dell
mode: solo
turns: 10
narrator_stub: deterministic
narrator_stub_latency_ms: 8000  # representative warm-Opus latency
assertions:
  - preprocess_llm_absent_or_zero
  - total_ms_median_below_baseline_minus_5000ms
```

- [ ] **Step 3: Run the scenario (expect PASS or document the baseline)**

If the runner accepts the YAML directly:
```bash
just playtest-scenario localdm-offline-latency
```

If a baseline file does not yet exist, the run will record a baseline rather than asserting against it — that's fine for the first execution.

- [ ] **Step 4: Capture the baseline as a checked-in artifact**

If the runner produces a baseline file (e.g., `scenarios/localdm-offline-latency.baseline.json`), inspect it. Add it to git ONLY if it's small and stable. Otherwise document the recording procedure in the YAML's preamble.

- [ ] **Step 5: Commit**

```bash
git add scenarios/localdm-offline-latency.yaml
# add scenarios/localdm-offline-latency.baseline.json only if produced and small
git commit -m "test(scenarios): latency benchmark for LocalDM offline path

Drives 10 solo turns and asserts the preprocess_llm phase is gone and
total_ms median dropped 5+ seconds vs a pre-change baseline. Locks
success criterion #1 of the spec.
"
```

If the project has no scenario-runner infrastructure capable of asserting on `phase_durations_ms`, this task degrades to: write a manual playtest checklist alongside the spec under `docs/playtest-script.md` describing how to capture phase timings before/after and visually compare. Do not invent a benchmark runner from scratch in this story — flag it as out-of-scope and proceed.

---

## Task 13: Update architecture.md and CLAUDE.md references

**Files:**
- Modify: `/Users/slabgorb/Projects/oq-2/docs/architecture.md`
- Modify: any other doc that references LocalDM as live

- [ ] **Step 1: Audit doc references**

Run from project root:
```bash
grep -rn "LocalDM\|local_dm\|preprocess_llm\|decomposer" docs/ CLAUDE.md README.md 2>/dev/null
```

Expected hits in:
- `docs/architecture.md` — section likely mentions LocalDM in agent layer
- `CLAUDE.md` — agents/ description mentions "preprocessor"
- `docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md` — original LocalDM spec (do not edit; just reference from your notes)

- [ ] **Step 2: Update each doc**

For `docs/architecture.md`, find the section describing the agent layer and add a one-line note that LocalDM is dormant on the live turn path as of 2026-04-28, with a reference to the new spec.

For `CLAUDE.md`'s `sidequest-server/sidequest/agents/` description ("Claude CLI subprocess orchestration (narrator, preprocessor)"), update to "(narrator; LocalDM preprocessor is dormant per 2026-04-28 spec)".

For `docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md`, add a header note at the top: "**Superseded 2026-04-28** — see `2026-04-28-localdm-offline-only-design.md`. This spec's "LocalDM is on the live critical path" assumption no longer holds."

- [ ] **Step 3: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2
git add docs/architecture.md CLAUDE.md docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md
git commit -m "docs: reflect LocalDM dormancy on live turn path

Updates architecture.md and CLAUDE.md to point at the new
localdm-offline-only spec; adds a supersession header to the original
LocalDM decomposer spec so future readers don't assume it's live.
"
```

---

## Task 14: Final verification

**Files:**
- None (verification only)

- [ ] **Step 1: Run the full test suite from `sidequest-server/`**

```bash
uv run pytest --tb=short
```

Expected: 100% pass or skip. The skip count includes the Group G quarantines from Task 7.

- [ ] **Step 2: Run lint**

```bash
uv run ruff check .
```

Expected: no NEW errors. Pre-existing baseline errors stay. If a NEW error was introduced by these changes, fix it.

- [ ] **Step 3: Confirm no `sd.local_dm` or `LocalDM(` references remain in non-test code**

```bash
grep -rn "sd\.local_dm\|LocalDM(" sidequest/ --include="*.py"
```

Expected: zero hits.

- [ ] **Step 4: Confirm `local_dm.decompose` OTEL span is gone**

```bash
grep -rn "local_dm\|preprocess_llm" sidequest/server/ --include="*.py"
```

Expected: zero hits in `sidequest/server/`. The `preprocess_llm` timings phase is removed because the LocalDM block that defined it is removed.

- [ ] **Step 5: One real solo session**

Start the stack:
```bash
just up
```

In the UI, start a fresh solo game (`caverns_and_claudes` is a known-working pack), play 5–10 turns. Visually confirm:
- Turns feel faster than before (subjective).
- No errors in `/tmp/sidequest-server.log` mentioning LocalDM, dispatch_package, or visibility_sidecar.
- Narration quality is acceptable (no obvious referent confusion).

If something is broken, file the regression in the user's playtest scratch file (do NOT file Jira). Fix before considering this plan complete.

- [ ] **Step 6: Capture the corpus from the live session**

```bash
ls ~/.sidequest/saves/caverns_and_claudes/dell/<player>/save.db
uv run python -m sidequest.corpus.miner --save <path> --out /tmp/post-change-corpus.jsonl
head -3 /tmp/post-change-corpus.jsonl
```

Expected: ~5–10 lines of JSON, each a valid `TrainingPair` with non-empty `input_text` and `output_text`. This is the live confirmation of success criterion #3.

If the miner has a different invocation pattern (different module, no `--out` flag), substitute. Find the actual entry point in Step 4's grep output if needed.

- [ ] **Step 7: Done**

No commit. This task is verification only.

---

## Self-Review Checklist (post-write)

Before handing this plan to executor:

- [ ] Every task has at least one Step that produces concrete output (test, edit, commit).
- [ ] Every step that changes code shows the actual code, not "implement here".
- [ ] No "TBD", "TODO", "later", "etc.".
- [ ] Type and method names used in later tasks match earlier tasks.
- [ ] Spec coverage:
  - §Goal — covered by Tasks 4, 14.
  - §Components items 1–4 (file changes) — covered by Tasks 4, 5, 6, 8, 9, 10.
  - §Components item 5 (corpus) — pivoted to Task 11 (miner verification).
  - §Components item 6 (OTEL) — `local_dm.decompose` span removed implicitly by Task 4 (removing the call removes the `with` span); verified by Task 14 Step 4.
  - §Data Flow — covered by Tasks 4, 5, 6.
  - §Error Handling — narrator-failure paths unchanged; latent reader audit is Task 1.
  - §Testing — covered by Tasks 2, 3, 7, 11, 12.
  - §Risks — dormant code rot mitigation covered by Tasks 9, 10 (markers); ADR status open → noted as out of scope.
  - §Success Criteria 1–4 — Tasks 12, 14, 11, 14 respectively. #5 (playtest) covered by Task 14 Step 5.
- [ ] No spec requirement without a task. Confirmed.
