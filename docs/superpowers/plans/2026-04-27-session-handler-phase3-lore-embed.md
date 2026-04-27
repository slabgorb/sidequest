# Session Handler Phase 3 — Lore / Embed Worker Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract three lore/embed-worker methods from `WebSocketSessionHandler` (post-Phase-2 4693-line `session_handler.py`) into a new sibling module `sidequest-server/sidequest/server/dispatch/lore_embed.py`, with byte-identical behavior, mandatory wiring tests, preserved OTEL span surface, and the `embed_task` lifecycle on `_SessionData` untouched (cleanup-cancel must still work).

**Architecture:** Each extracted method becomes a free function in `lore_embed.py` that takes `handler: WebSocketSessionHandler` as its first argument. The original method on `WebSocketSessionHandler` becomes a thin delegate calling the new free function. No new abstractions, no narrow context dataclasses, no class hierarchies. Behavior is preserved verbatim. Same pattern that shipped in Phases 1 and 2.

**Tech Stack:** Python 3.12, FastAPI/Uvicorn, pytest, `uv` package manager. Tests run via `just server-test` from orchestrator root or `uv run pytest -v` from `sidequest-server/`.

**Spec:** `docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md` (Phase 3 — Lore / Embed Worker → `server/dispatch/lore_embed.py`).

**Branch baseline:** `sidequest-server/develop` at `c2499bc` (Phase 2 post-epic cleanup merge). Feature branch: `refactor/session-handler-phase3-lore-embed`.

**Out of scope for this plan:** Phases 4–8 (media, chargen, small handlers, connect, narration turn). Each gets its own plan after this one merges. Removal of the three thin delegate methods is deferred to a post-epic cleanup PR per the Phase 2 pattern.

---

## Standing Rules — applied to every implementer subagent prompt

These are non-negotiable. Subagent prompts MUST repeat them verbatim because subagents do not inherit user-memory rules:

- **NEVER use `git stash`.** Standing user rule. If WIP needs to land somewhere, commit it on the feature branch. Phase 1 had a violation; Phase 2 implementers were re-instructed each time and complied. Re-state for every Phase 3 task.
- **DO NOT MODIFY the skeleton import-existence test** (`test_lore_embed_module_exposes_required_functions`) until the LAST extraction task lands. It is **intentionally RED** as the epic-level RED→GREEN gate. Subagents tried to "fix" the equivalent test in Phases 1 and 2 and were wrong.
- **Pre-existing failures on `c2499bc` are NOT yours to fix.** As of the Phase 2 post-epic merge there is exactly one persistent red test plus one flaky-pre-existing test:
  - `tests/server/dispatch/test_sealed_letter_dispatch_integration.py::test_legacy_beat_selection_path_still_works` — persistently red.
  - `tests/server/test_visual_style_lora_removal_wiring` — content-repo state-dependent; sometimes red, sometimes green; treat as flaky-pre-existing if it appears.
  If Phase 3 breaks any of the OTHER passing tests, that is a regression you must fix.
- **Pre-existing lint warnings on `develop@c2499bc` are out of scope.** As of c2499bc:
  - `SIM102` at `sidequest/server/views.py:90` (relocated by Phase 2; not part of Phase 3 cluster)
  - `SIM105` at `sidequest/server/session_handler.py:859` (line shifts as `session_handler.py` shrinks; not in Phase 3 cluster)
  Do not "improve" them — pure decomposition only.
- **Pin working directory:** `/Users/slabgorb/Projects/oq-2/sidequest-server`.
- **Pin branch:** `refactor/session-handler-phase3-lore-embed`.
- **Pinned baseline SHA:** `c2499bc` on `sidequest-server/develop`. Verify with `git -C /Users/slabgorb/Projects/oq-2/sidequest-server merge-base HEAD origin/develop` before starting each task.
- **Use the orchestrator's `just` recipes when verifying** (`just server-test`, `just server-lint`, `just server-check`) — but per-test invocations via `uv run pytest tests/...` are fine for tight loops. **Use `uv run pytest`, NEVER bare `pytest`.**
- **Behavior preservation is byte-identical.** The only acceptable diff in moved code is:
  - `self.X` → `handler.X` (forced by extraction)
  - `self._other_method(...)` → in-module function call when `other` was also extracted (e.g., `self._run_embed_worker(...)` → `run_worker(...)`)
  - Removing the underscore prefix on the renamed function
  - Replacing `tracer = trace.get_tracer("sidequest.server.session_handler")` with `tracer = trace.get_tracer("sidequest.server.dispatch.lore_embed")` is **not** allowed — keep the tracer name verbatim so OTEL consumers don't see a span-source rename. The tracer name is byte-identical.
  Anything else gets logged in the PR body as an explicit deviation.
- **Spec drift on `_run_embed_worker` signature:** the spec public surface lists `async def run_worker(handler, sd: _SessionData) -> None`, but the actual method takes `(self, sd, pending_count, turn_number)`. The plan uses the **actual** signature `(handler, sd, pending_count, turn_number)`. This is a spec-text-only inaccuracy, not a behavioral change — the in-module call from `dispatch_worker` already passes those arguments today. Phase 2 hit the same kind of drift on `backfill_last_narration_block`'s signature; we follow the implementation, not the spec sketch.

## Pre-flight verification — already complete

These were checked while authoring this plan; record here so the implementer doesn't re-do them:

- **Source method locations (verified by grep on `c2499bc`):**
  - `_retrieve_lore_for_turn` at `session_handler.py:4272-4305` (~34 lines)
  - `_dispatch_embed_worker` at `session_handler.py:4307-4347` (~41 lines)
  - `_run_embed_worker` at `session_handler.py:4349-4380` (~32 lines)
  - **Spec line numbers (4869/4904/4946) drifted ~600 lines** because Phase 1 + Phase 2 shrank the file. Use the live grep, not the spec line numbers.

- **Monkeypatch landmines:** `grep -rn "monkeypatch.*\(_retrieve_lore_for_turn\|_dispatch_embed_worker\|_run_embed_worker\|retrieve_for_turn\|dispatch_worker\|run_worker\)" sidequest-server/tests/` returned **NO MATCHES**. There are no `monkeypatch.setattr` patches against lore-cluster symbols today. **Implication:** all imports in `lore_embed.py` may be eager (module-level) — there is no monkeypatch-reachability constraint forcing lazy imports. (We will use eager imports because the code references `asyncio`, `trace`, `embed_pending_fragments`, `retrieve_lore_context`, and `_watcher_publish` at runtime, and there is no circular-import risk — these come from telemetry and game submodules, not from `sidequest.server`.)

- **Direct attribute reassignment landmines:** `grep -rn "handler\._\(retrieve_lore_for_turn\|dispatch_embed_worker\|run_embed_worker\) = " sidequest-server/tests/` returned **NO MATCHES**. The Phase 2 `test_perception_rewriter_wiring.py:262/314` issue (`handler.status_effects_by_player = lambda: ...`) does not recur for Phase 3.

- **External (production) callers of the three methods:**
  - `_retrieve_lore_for_turn`: called at `session_handler.py:999, 2939, 3816` (three production call sites — narration turn pipeline; will eventually go through `lore_embed.retrieve_for_turn(self, sd, action)` in Phase 8 when narration_turn extracts).
  - `_dispatch_embed_worker`: called at `session_handler.py:3230` (one production call site — narration turn post-turn).
  - `_run_embed_worker`: called only from `_dispatch_embed_worker` (`session_handler.py:4347`) — internal task body, no external callers.
  - All three production callsites continue to work through the thin delegates; no caller-side changes in this PR.

- **Test callers (`tests/server/test_lore_rag_wiring.py`):**
  - Three direct `handler._dispatch_embed_worker(sd)` calls at lines 336, 411, 425 — go through the delegate, survive untouched.
  - Multiple `sd.embed_task is not None` and `sd.embed_task is first_task` assertions exercise the lifecycle. The lifecycle stays on `_SessionData` (out of scope per spec); these tests must continue to pass without modification.
  - `cleanup()` cancellation test (`test_cleanup_cancels_in_flight_embed_task` at line 289) exercises `session_handler.cleanup` which stays in `session_handler.py` (lines 792-801, untouched by Phase 3).

- **`_watcher_publish` import path verification:** `_watcher_publish` is the alias in `session_handler.py:152` for `sidequest.telemetry.watcher_hub.publish_event`. **Decision: import directly from the canonical source** in `lore_embed.py` — `from sidequest.telemetry.watcher_hub import publish_event as _watcher_publish` — preserving the local name. This avoids replicating Phase 1's `emitters.py` logger-debt pattern (which imports `_watcher_publish` and `logger` from `sidequest.server.session_handler` lazily inside function bodies).

- **`logger` ownership:** new module gets its own `logger = logging.getLogger(__name__)` at module scope from the start. Per the handoff, this is the established pattern post-Phase-2 (views.py owns its logger; emitters.py debt remains as a separate cleanup chore).

- **`retrieve_lore_context` and `embed_pending_fragments` import path:** both live at `sidequest.game.lore_embedding`. Verified at `session_handler.py:53-56`.

- **Cross-module references:** No external module references `_retrieve_lore_for_turn`, `_dispatch_embed_worker`, or `_run_embed_worker` other than `session_handler.py` itself plus `tests/server/test_lore_rag_wiring.py` (the canonical wiring test for this cluster).

- **`dispatch/__init__.py`:** intentionally empty of re-exports (file:1-12). No modification needed; `lore_embed.py` is imported by FQN.

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `sidequest-server/sidequest/server/dispatch/lore_embed.py` | **Create** | Houses three free functions: `retrieve_for_turn`, `dispatch_worker`, `run_worker`. Owns its own `logger` and imports `_watcher_publish` from the canonical telemetry source. |
| `sidequest-server/sidequest/server/session_handler.py` | **Modify** | The three method bodies are replaced with thin delegates calling the free functions. All other content untouched. The `cleanup()` block at file:792-801 (which cancels `sd.embed_task`) is **NOT** modified — it operates on the `_SessionData` attribute, not on the worker method. |
| `sidequest-server/tests/server/dispatch/test_lore_embed.py` | **Create** | Wiring tests for each of the three delegates plus a behavioral test for the simplest function (`retrieve_for_turn` happy path delegating to `retrieve_lore_context`). The existing `tests/server/test_lore_rag_wiring.py` continues to pass without modification — that's the canonical end-to-end wiring guard for this cluster. |

The three functions are extracted in dependency order:

1. `retrieve_for_turn` first (no in-cluster callers; isolated)
2. `run_worker` next (no in-cluster callers; will be called by `dispatch_worker` in step 3)
3. `dispatch_worker` last (calls in-module `run_worker`)

This order means each task's extracted function has its in-cluster dependencies already extracted.

---

## Task 1: Create empty `lore_embed.py` and confirm the import-existence test fails

**Files:**
- Create: `sidequest-server/sidequest/server/dispatch/lore_embed.py`
- Create: `sidequest-server/tests/server/dispatch/test_lore_embed.py`
- Verify: `sidequest-server/tests/server/dispatch/__init__.py` exists (it should — Phase 1's emitters or other dispatch tests created it). If not, create empty.

- [ ] **Step 1.1: Verify the test directory exists**

```bash
ls sidequest-server/tests/server/dispatch/
```

If `__init__.py` is missing, create an empty one:
```bash
touch sidequest-server/tests/server/dispatch/__init__.py
```

- [ ] **Step 1.2: Create the empty module file**

Create `sidequest-server/sidequest/server/dispatch/lore_embed.py` with this exact content:

```python
"""Lore RAG retrieval and embed-worker dispatch.

Phase 3 of the session_handler.py decomposition (see
docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md).

Each function takes ``handler: WebSocketSessionHandler`` as its first
argument. No new abstractions introduced — this is pure extraction
with byte-identical behavior to the original methods on
WebSocketSessionHandler.

The ``embed_task`` lifecycle remains on ``_SessionData`` (created by
``dispatch_worker`` here, cancelled by ``WebSocketSessionHandler.cleanup``
in ``session_handler.py``). That asymmetry is intentional — the task
attribute is shared session state, not worker-module state.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from opentelemetry import trace

from sidequest.game.lore_embedding import (
    embed_pending_fragments,
    retrieve_lore_context,
)
from sidequest.telemetry.watcher_hub import publish_event as _watcher_publish

if TYPE_CHECKING:
    from sidequest.server.session_handler import WebSocketSessionHandler, _SessionData

logger = logging.getLogger(__name__)
```

- [ ] **Step 1.3: Create the test file with one failing import-existence test**

Create `sidequest-server/tests/server/dispatch/test_lore_embed.py` with this exact content:

```python
"""Unit + wiring tests for sidequest/server/dispatch/lore_embed.py.

Phase 3 of session_handler decomposition. These tests verify:
1. Each extracted function exists with the expected signature.
2. The thin delegate methods on WebSocketSessionHandler still call
   into lore_embed.py (wiring guard per CLAUDE.md).
3. Behavior is preserved (functional parity with the pre-extraction
   methods) — supplemented by the canonical end-to-end wiring guard
   in tests/server/test_lore_rag_wiring.py which continues to
   exercise the full pipeline through the delegates.
"""

from __future__ import annotations


def test_lore_embed_module_exposes_required_functions() -> None:
    """Wiring guard — the three required functions must be importable
    from sidequest.server.dispatch.lore_embed by their canonical names.

    DO NOT MODIFY this test until the last extraction (Task 4) lands.
    It is INTENTIONALLY RED until then — the epic-level RED→GREEN gate
    that proves all three moves completed.
    """
    from sidequest.server.dispatch import lore_embed

    assert hasattr(lore_embed, "retrieve_for_turn")
    assert hasattr(lore_embed, "dispatch_worker")
    assert hasattr(lore_embed, "run_worker")
```

- [ ] **Step 1.4: Run the test and confirm it fails**

Run from `sidequest-server/`:
```bash
uv run pytest tests/server/dispatch/test_lore_embed.py::test_lore_embed_module_exposes_required_functions -v
```

Expected: FAIL with `AssertionError` — the three functions do not exist yet. This is the intentional epic-level RED.

- [ ] **Step 1.5: Commit the skeleton**

```bash
git add sidequest-server/sidequest/server/dispatch/lore_embed.py sidequest-server/tests/server/dispatch/test_lore_embed.py
# also git add sidequest-server/tests/server/dispatch/__init__.py if you created it in Step 1.1
git commit -m "refactor(server): create lore_embed.py skeleton (Phase 3 of session_handler decomposition)"
```

---

## Task 2: Extract `_retrieve_lore_for_turn` → `lore_embed.retrieve_for_turn`

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/lore_embed.py`
- Modify: `sidequest-server/sidequest/server/session_handler.py:4272-4305`
- Modify: `sidequest-server/tests/server/dispatch/test_lore_embed.py`

> **Why this method first:** zero in-cluster dependencies (no calls to other Phase 3 methods), and the simplest body of the three. Establishes the extraction pattern before tackling `dispatch_worker`'s in-module call to `run_worker`.

- [ ] **Step 2.1: Add wiring test**

Append to `sidequest-server/tests/server/dispatch/test_lore_embed.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_retrieve_for_turn_delegate_calls_module_function(
    monkeypatch, session_handler_factory
) -> None:
    """Wiring guard — WebSocketSessionHandler._retrieve_lore_for_turn
    must delegate to lore_embed.retrieve_for_turn."""
    from sidequest.server.dispatch import lore_embed

    sd, handler = session_handler_factory()
    captured: list[tuple] = []
    sentinel: str | None = "<lore-block-sentinel>"

    async def _spy(h, sd_arg, action):
        captured.append((h, sd_arg, action))
        return sentinel

    monkeypatch.setattr(lore_embed, "retrieve_for_turn", _spy)

    result = await handler._retrieve_lore_for_turn(sd, "look around")

    assert result == sentinel
    assert captured == [(handler, sd, "look around")]
```

- [ ] **Step 2.2: Run the wiring test — confirm it fails**

```bash
uv run pytest tests/server/dispatch/test_lore_embed.py::test_retrieve_for_turn_delegate_calls_module_function -v
```

Expected: FAIL — `lore_embed.retrieve_for_turn` does not exist yet, or the delegate still owns the implementation.

- [ ] **Step 2.3: Add the function to `lore_embed.py`**

Append to `sidequest-server/sidequest/server/dispatch/lore_embed.py`:

```python
async def retrieve_for_turn(
    handler: WebSocketSessionHandler,
    sd: _SessionData,
    action: str,
) -> str | None:
    """Fetch the pre-turn lore block via semantic search.

    Always returns ``None`` on empty stores, missing daemons, or
    embed failures — the narrator will run without RAG injection,
    which is strictly better than crashing the turn. Expected failure
    modes (empty store, daemon unavailable, embed error, query too
    large) are logged inside :func:`retrieve_lore_context` and surface
    their own OTEL span attribute. The blanket ``except Exception``
    below exists precisely for paths those guards do not cover (e.g.
    a malformed daemon reply that raises ``KeyError`` from
    ``EmbedResponse`` construction) so a buggy codepath never crashes
    the turn.
    """
    try:
        return await retrieve_lore_context(sd.lore_store, action)
    except Exception as exc:  # noqa: BLE001 — RAG must never crash a turn
        logger.warning(
            "lore_retrieval.unexpected_exception action_len=%d error=%s",
            len(action),
            exc,
        )
        _watcher_publish(
            "state_transition",
            {
                "field": "lore_retrieval",
                "op": "failed",
                "reason": "unexpected_exception",
                "error": type(exc).__name__,
            },
            component="lore",
            severity="error",
        )
        return None
```

> **Note on `handler` parameter:** the function takes `handler` for signature uniformity even though the body never reads from it. Phase 2's `is_hidden_status_list` did the same — uniform signature now means uniform refactor later when delegates drop. (`handler` is unused-but-required; no `_` prefix because the convention across all extracted methods is `handler` as first positional.)

- [ ] **Step 2.4: Replace the method body in `session_handler.py`**

In `sidequest-server/sidequest/server/session_handler.py`, find this block (currently at file:4272-4305):

```python
    async def _retrieve_lore_for_turn(self, sd: _SessionData, action: str) -> str | None:
        """Fetch the pre-turn lore block via semantic search.

        ...

        the turn.
        """
        try:
            return await retrieve_lore_context(sd.lore_store, action)
        except Exception as exc:  # noqa: BLE001 — RAG must never crash a turn
            logger.warning(
                "lore_retrieval.unexpected_exception action_len=%d error=%s",
                len(action),
                exc,
            )
            _watcher_publish(
                "state_transition",
                {
                    "field": "lore_retrieval",
                    "op": "failed",
                    "reason": "unexpected_exception",
                    "error": type(exc).__name__,
                },
                component="lore",
                severity="error",
            )
            return None
```

Replace its full body with:

```python
    async def _retrieve_lore_for_turn(self, sd: _SessionData, action: str) -> str | None:
        """Pre-turn lore RAG retrieval. Delegates to ``lore_embed.retrieve_for_turn``.

        Phase 3 of session_handler decomposition (see
        docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md).
        """
        from sidequest.server.dispatch import lore_embed

        return await lore_embed.retrieve_for_turn(self, sd, action)
```

- [ ] **Step 2.5: Run the wiring test — confirm it passes**

```bash
uv run pytest tests/server/dispatch/test_lore_embed.py::test_retrieve_for_turn_delegate_calls_module_function -v
```

Expected: PASS.

- [ ] **Step 2.6: Add a behavioral unit test for the function itself**

> **Critical note on monkeypatch target:** because `lore_embed.py` does `from sidequest.game.lore_embedding import retrieve_lore_context`, the name `retrieve_lore_context` is pulled into `lore_embed`'s namespace at import time. To intercept the call, you must patch the **caller's** namespace (`lore_embed.retrieve_lore_context`), NOT the source module (`sidequest.game.lore_embedding.retrieve_lore_context`). Patching the source module would have no effect because the `await retrieve_lore_context(...)` call inside `lore_embed.retrieve_for_turn` resolves the name through `lore_embed`'s globals, which already hold the bound reference.

Append to `sidequest-server/tests/server/dispatch/test_lore_embed.py`:

```python
@pytest.mark.asyncio
async def test_retrieve_for_turn_returns_none_on_unexpected_exception(
    monkeypatch, session_handler_factory
) -> None:
    """Behavioral test — when retrieve_lore_context raises an unexpected
    exception, retrieve_for_turn must swallow it, log a warning, emit a
    failure watcher event, and return None. The turn must never crash
    on RAG failure (CLAUDE.md "No Silent Fallbacks" carve-out: the
    fallback is loud-via-OTEL, silent-to-the-caller-by-design)."""
    from sidequest.server.dispatch import lore_embed

    sd, handler = session_handler_factory()

    async def _boom(*args, **kwargs):
        raise KeyError("simulated malformed embed response")

    # Patch the caller's namespace, not sidequest.game.lore_embedding —
    # see "Critical note on monkeypatch target" above.
    monkeypatch.setattr(lore_embed, "retrieve_lore_context", _boom)

    captured_events: list[tuple] = []

    def _capture(event_kind, payload, component=None, severity=None):
        captured_events.append((event_kind, payload, component, severity))

    monkeypatch.setattr(lore_embed, "_watcher_publish", _capture)

    result = await lore_embed.retrieve_for_turn(handler, sd, "look around")

    assert result is None
    assert len(captured_events) == 1
    kind, payload, component, severity = captured_events[0]
    assert kind == "state_transition"
    assert payload["field"] == "lore_retrieval"
    assert payload["op"] == "failed"
    assert payload["reason"] == "unexpected_exception"
    assert payload["error"] == "KeyError"
    assert component == "lore"
    assert severity == "error"
```

- [ ] **Step 2.7: Run the new behavioral test plus the canonical end-to-end wiring test**

```bash
uv run pytest tests/server/dispatch/test_lore_embed.py tests/server/test_lore_rag_wiring.py -v
```

Expected: all PASS. The existing `test_lore_rag_wiring.py` exercises the full pipeline (`WebSocketSessionHandler → _retrieve_lore_for_turn → retrieve_lore_context → TurnContext → narrator prompt`) via the delegate, which now routes through `lore_embed.retrieve_for_turn`.

- [ ] **Step 2.8: Run the full server test suite**

```bash
uv run pytest -v
```

Expected: all PASS except the pre-existing failures listed in Standing Rules. If anything else fails, the extraction broke behavior — stop and investigate before committing.

- [ ] **Step 2.9: Commit**

```bash
git add sidequest-server/sidequest/server/dispatch/lore_embed.py sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/dispatch/test_lore_embed.py
git commit -m "refactor(server): extract _retrieve_lore_for_turn to lore_embed module"
```

---

## Task 3: Extract `_run_embed_worker` → `lore_embed.run_worker`

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/lore_embed.py`
- Modify: `sidequest-server/sidequest/server/session_handler.py:4349-4380`
- Modify: `sidequest-server/tests/server/dispatch/test_lore_embed.py`

> **Why this before `dispatch_worker`:** `dispatch_worker` calls `run_worker` via `asyncio.create_task(run_worker(...))`. Extracting `run_worker` first means Task 4's `dispatch_worker` extraction has its in-cluster dependency already in `lore_embed.py` and can call it as a bare in-module name.

> **Spec drift note:** the spec lists the public surface as `async def run_worker(handler, sd: _SessionData) -> None`. The actual signature is `(self, sd, pending_count, turn_number)`. We use the actual signature — it is the only one that compiles against the existing in-module call from `dispatch_worker`. See Standing Rules → "Spec drift on `_run_embed_worker` signature".

- [ ] **Step 3.1: Add wiring test**

Append to `sidequest-server/tests/server/dispatch/test_lore_embed.py`:

```python
@pytest.mark.asyncio
async def test_run_worker_delegate_calls_module_function(
    monkeypatch, session_handler_factory
) -> None:
    """Wiring guard — WebSocketSessionHandler._run_embed_worker
    must delegate to lore_embed.run_worker."""
    from sidequest.server.dispatch import lore_embed

    sd, handler = session_handler_factory()
    captured: list[tuple] = []

    async def _spy(h, sd_arg, pending_count, turn_number):
        captured.append((h, sd_arg, pending_count, turn_number))

    monkeypatch.setattr(lore_embed, "run_worker", _spy)

    await handler._run_embed_worker(sd, 7, 42)

    assert captured == [(handler, sd, 7, 42)]
```

- [ ] **Step 3.2: Run the wiring test — confirm it fails**

```bash
uv run pytest tests/server/dispatch/test_lore_embed.py::test_run_worker_delegate_calls_module_function -v
```

Expected: FAIL.

- [ ] **Step 3.3: Move the body into `lore_embed.py`**

Append to `sidequest-server/sidequest/server/dispatch/lore_embed.py`:

```python
async def run_worker(
    handler: WebSocketSessionHandler,
    sd: _SessionData,
    pending_count: int,
    turn_number: int,
) -> None:
    """Background embed worker — never raises, always emits telemetry."""
    try:
        result = await embed_pending_fragments(sd.lore_store)
    except Exception as exc:  # noqa: BLE001 — worker cannot crash the loop
        logger.exception("lore_embedding.worker_exception")
        _watcher_publish(
            "state_transition",
            {
                "field": "lore_embedding",
                "op": "failed",
                "reason": "exception",
                "error": type(exc).__name__,
                "turn_number": turn_number,
            },
            component="lore",
            severity="error",
        )
        return
    _watcher_publish(
        "state_transition",
        {
            "field": "lore_embedding",
            "op": "completed",
            "pending_at_dispatch": pending_count,
            "turn_number": turn_number,
            **result.as_dict(),
        },
        component="lore",
    )
```

> **Note on `handler` parameter:** unused in the body (same as `retrieve_for_turn`'s case). Kept for signature uniformity across the cluster.

- [ ] **Step 3.4: Replace the method body in `session_handler.py`**

In `sidequest-server/sidequest/server/session_handler.py`, find this block (currently at file:4349-4380):

```python
    async def _run_embed_worker(
        self, sd: _SessionData, pending_count: int, turn_number: int
    ) -> None:
        """Background embed worker — never raises, always emits telemetry."""
        try:
            result = await embed_pending_fragments(sd.lore_store)
        except Exception as exc:  # noqa: BLE001 — worker cannot crash the loop
            logger.exception("lore_embedding.worker_exception")
            _watcher_publish(
                ...
            )
            return
        _watcher_publish(
            ...
        )
```

Replace its full body with:

```python
    async def _run_embed_worker(
        self, sd: _SessionData, pending_count: int, turn_number: int
    ) -> None:
        """Background embed worker. Delegates to ``lore_embed.run_worker``.

        Phase 3 of session_handler decomposition (see
        docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md).
        """
        from sidequest.server.dispatch import lore_embed

        await lore_embed.run_worker(self, sd, pending_count, turn_number)
```

- [ ] **Step 3.5: Run the wiring test — confirm it passes**

```bash
uv run pytest tests/server/dispatch/test_lore_embed.py::test_run_worker_delegate_calls_module_function -v
```

Expected: PASS.

- [ ] **Step 3.6: Run the canonical end-to-end wiring tests**

```bash
uv run pytest tests/server/test_lore_rag_wiring.py -v
```

Expected: all PASS. The worker-task tests (`test_dispatch_embed_worker_stores_lifecycle_task`, `test_double_dispatch_skipped_while_worker_running`, `test_cleanup_cancels_in_flight_embed_task`) exercise the worker through the delegate.

- [ ] **Step 3.7: Run the full server test suite**

```bash
uv run pytest -v
```

Expected: all PASS except the pre-existing failures.

- [ ] **Step 3.8: Commit**

```bash
git add sidequest-server/sidequest/server/dispatch/lore_embed.py sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/dispatch/test_lore_embed.py
git commit -m "refactor(server): extract _run_embed_worker to lore_embed module"
```

---

## Task 4: Extract `_dispatch_embed_worker` → `lore_embed.dispatch_worker`

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/lore_embed.py`
- Modify: `sidequest-server/sidequest/server/session_handler.py:4307-4347`
- Modify: `sidequest-server/tests/server/dispatch/test_lore_embed.py`

> **Note on intra-module call:** `self._run_embed_worker(sd, len(pending), turn_number)` becomes `run_worker(handler, sd, len(pending), turn_number)` (the in-module free function from Task 3). The handler delegate is reserved for callers outside this module — but this method is the only caller of `_run_embed_worker` anywhere in the codebase, so post-epic cleanup will eventually drop the delegate and route the production callsite at `session_handler.py:3230` directly to `lore_embed.dispatch_worker`. Out of scope for this PR.

> **Note on tracer name:** the original method calls `tracer = trace.get_tracer("sidequest.server.session_handler")`. Per Standing Rules → "Behavior preservation is byte-identical", **do not rename the tracer to `"sidequest.server.dispatch.lore_embed"`** even though that would feel more correct. OTEL consumers (the GM panel watcher) key off this string; renaming it would be a behavioral change disguised as cleanup. The tracer string is preserved verbatim.

- [ ] **Step 4.1: Add wiring test**

Append to `sidequest-server/tests/server/dispatch/test_lore_embed.py`:

```python
def test_dispatch_worker_delegate_calls_module_function(
    monkeypatch, session_handler_factory
) -> None:
    """Wiring guard — WebSocketSessionHandler._dispatch_embed_worker
    must delegate to lore_embed.dispatch_worker."""
    from sidequest.server.dispatch import lore_embed

    sd, handler = session_handler_factory()
    captured: list[tuple] = []

    def _spy(h, sd_arg):
        captured.append((h, sd_arg))

    monkeypatch.setattr(lore_embed, "dispatch_worker", _spy)

    handler._dispatch_embed_worker(sd)

    assert captured == [(handler, sd)]
```

- [ ] **Step 4.2: Run the wiring test — confirm it fails**

```bash
uv run pytest tests/server/dispatch/test_lore_embed.py::test_dispatch_worker_delegate_calls_module_function -v
```

Expected: FAIL.

- [ ] **Step 4.3: Move the body into `lore_embed.py`**

Append to `sidequest-server/sidequest/server/dispatch/lore_embed.py`:

```python
def dispatch_worker(handler: WebSocketSessionHandler, sd: _SessionData) -> None:
    """Spawn a background embed worker for any newly-added lore.

    Fire-and-forget, but lifecycle-tracked. The worker itself checks
    :meth:`DaemonClient.is_available` before opening any connection
    and returns early with ``skipped_daemon_unavailable=True`` when
    the sidecar is absent — matching the render-dispatch graceful
    degradation pattern.

    Double-dispatch gate: if a previous worker for this session is
    still running, skip this turn's dispatch. The next turn will pick
    up the remaining pending fragments. This prevents two concurrent
    workers from racing at the ``await client.embed()`` yield point
    and double-incrementing the retry counter on the same fragment.
    """
    tracer = trace.get_tracer("sidequest.server.session_handler")
    previous = sd.embed_task
    if previous is not None and not previous.done():
        # Emit a span for the skip so the GM panel's OTEL audit trail
        # shows it alongside the worker's own ``lore_embedding.worker``
        # span. Watcher event stays as well for the live state_transition
        # stream.
        with tracer.start_as_current_span("lore_embedding.dispatch_skipped") as skip_span:
            skip_span.set_attribute("lore.skip_reason", "worker_still_running")
            skip_span.set_attribute("lore.turn_number", sd.snapshot.turn_manager.interaction)
        _watcher_publish(
            "state_transition",
            {
                "field": "lore_embedding",
                "op": "skipped",
                "reason": "worker_still_running",
                "turn_number": sd.snapshot.turn_manager.interaction,
            },
            component="lore",
        )
        return
    pending = sd.lore_store.pending_embedding_ids(max_retries=3)
    if not pending:
        return
    turn_number = sd.snapshot.turn_manager.interaction
    sd.embed_task = asyncio.create_task(run_worker(handler, sd, len(pending), turn_number))
```

> **Diff from original (line-by-line):** identical except the last line. Original:
> ```python
> sd.embed_task = asyncio.create_task(self._run_embed_worker(sd, len(pending), turn_number))
> ```
> New:
> ```python
> sd.embed_task = asyncio.create_task(run_worker(handler, sd, len(pending), turn_number))
> ```
> Two changes: `self._run_embed_worker(sd, ...)` → `run_worker(handler, sd, ...)`. Pass `handler` explicitly because `run_worker` requires it as first positional. Tracer name unchanged.

- [ ] **Step 4.4: Replace the method body in `session_handler.py`**

In `sidequest-server/sidequest/server/session_handler.py`, find this block (currently at file:4307-4347):

```python
    def _dispatch_embed_worker(self, sd: _SessionData) -> None:
        """Spawn a background embed worker for any newly-added lore.

        ...
        """
        tracer = trace.get_tracer("sidequest.server.session_handler")
        previous = sd.embed_task
        if previous is not None and not previous.done():
            ...
            return
        pending = sd.lore_store.pending_embedding_ids(max_retries=3)
        if not pending:
            return
        turn_number = sd.snapshot.turn_manager.interaction
        sd.embed_task = asyncio.create_task(self._run_embed_worker(sd, len(pending), turn_number))
```

Replace its full body with:

```python
    def _dispatch_embed_worker(self, sd: _SessionData) -> None:
        """Post-turn embed worker dispatch. Delegates to ``lore_embed.dispatch_worker``.

        Phase 3 of session_handler decomposition (see
        docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md).
        """
        from sidequest.server.dispatch import lore_embed

        lore_embed.dispatch_worker(self, sd)
```

- [ ] **Step 4.5: Run the wiring test — confirm it passes**

```bash
uv run pytest tests/server/dispatch/test_lore_embed.py::test_dispatch_worker_delegate_calls_module_function -v
```

Expected: PASS.

- [ ] **Step 4.6: Run the skeleton import-existence test — it must finally GO GREEN**

```bash
uv run pytest tests/server/dispatch/test_lore_embed.py::test_lore_embed_module_exposes_required_functions -v
```

Expected: **PASS for the first time.** All three functions are now extracted. The epic-level RED→GREEN gate has flipped.

- [ ] **Step 4.7: Run the canonical end-to-end wiring tests**

```bash
uv run pytest tests/server/test_lore_rag_wiring.py -v
```

Expected: all PASS. Particular tests of interest:
- `test_dispatch_embed_worker_stores_lifecycle_task` — exercises `dispatch_worker`'s `sd.embed_task = asyncio.create_task(...)` path through the delegate.
- `test_double_dispatch_skipped_while_worker_running` — exercises the early-return skip branch (the `tracer.start_as_current_span("lore_embedding.dispatch_skipped")` block).
- `test_cleanup_cancels_in_flight_embed_task` — exercises `cleanup()` which is **not** part of Phase 3 but operates on `sd.embed_task` set by `dispatch_worker`. Must continue to pass.

- [ ] **Step 4.8: Run the full server test suite**

```bash
uv run pytest -v
```

Expected: all PASS except the pre-existing failures.

- [ ] **Step 4.9: Commit**

```bash
git add sidequest-server/sidequest/server/dispatch/lore_embed.py sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/dispatch/test_lore_embed.py
git commit -m "refactor(server): extract _dispatch_embed_worker to lore_embed module"
```

---

## Task 5: OTEL parity verification

**Files:** none modified — read-only verification.

> **Why this task is short for Phase 3:** the lore/embed cluster owns exactly one OTEL span (`lore_embedding.dispatch_skipped` in `dispatch_worker`) and four `_watcher_publish` calls (one in `retrieve_for_turn` failure path, one in `dispatch_worker` skip branch, two in `run_worker`). The parity check is a quick before/after count.

- [ ] **Step 5.1: Confirm `_watcher_publish` count is preserved across `session_handler.py` + `lore_embed.py`**

```bash
# Baseline at branch base (Phase 2 post-epic merge c2499bc)
git -C sidequest-server show c2499bc:sidequest/server/session_handler.py | grep -cE "_watcher_publish\("
# Now (after Phase 3)
grep -cE "_watcher_publish\(" sidequest-server/sidequest/server/session_handler.py
grep -cE "_watcher_publish\(" sidequest-server/sidequest/server/dispatch/lore_embed.py
```

Expected: `(session_handler@c2499bc) == (session_handler now) + (lore_embed now)`. The lore cluster owned **4** `_watcher_publish` calls in the original methods, so `lore_embed.py` should report `4` and `session_handler.py` should report `4 less` than at `c2499bc`.

- [ ] **Step 5.2: Confirm `tracer.start_as_current_span` count is preserved**

```bash
# Baseline
git -C sidequest-server show c2499bc:sidequest/server/session_handler.py | grep -cE "tracer\.start_as_current_span"
# Now
grep -cE "tracer\.start_as_current_span" sidequest-server/sidequest/server/session_handler.py
grep -cE "tracer\.start_as_current_span" sidequest-server/sidequest/server/dispatch/lore_embed.py
```

Expected: `(session_handler@c2499bc) == (session_handler now) + (lore_embed now)`. The lore cluster owned **1** span (`lore_embedding.dispatch_skipped`), so `lore_embed.py` should report `1` and `session_handler.py` should report `1 less` than at `c2499bc`.

- [ ] **Step 5.3: Confirm tracer name preservation**

```bash
grep -E 'trace\.get_tracer\("[^"]+"\)' sidequest-server/sidequest/server/dispatch/lore_embed.py
```

Expected output:
```
    tracer = trace.get_tracer("sidequest.server.session_handler")
```

The tracer string is preserved verbatim per Standing Rules. Renaming it to `"sidequest.server.dispatch.lore_embed"` would be a behavioral change to OTEL consumers and is **out of scope**. (Out-of-scope reminder for the post-epic cleanup PR: the tracer rename should be a separate decision with explicit GM-panel telemetry coordination, not a refactor side-effect.)

- [ ] **Step 5.4: No commit — this task is verification only**

If parity is preserved, proceed to Task 6. If not, the most likely culprit is a missing `_watcher_publish` import or a tracer-name typo — read the diff and reconcile.

---

## Task 6: Final cleanup and integration check

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py` (line-count check only)

- [ ] **Step 6.1: Confirm `session_handler.py` line count dropped**

```bash
wc -l sidequest-server/sidequest/server/session_handler.py
```

Expected: approximately **4585 lines** (down from 4693 at `c2499bc`). Allow ±15 lines of variance from the spec's `-110` estimate — exact count depends on delegate-method docstring length.

- [ ] **Step 6.2: Run lint**

```bash
just server-lint
```

Or from `sidequest-server/`:
```bash
uv run ruff check .
```

Expected: clean (the two pre-existing warnings on `views.py:90` SIM102 and `session_handler.py:859` SIM105 may still be present — those are out of scope per Standing Rules; the SIM105 line number may have shifted as `session_handler.py` shrank further). If `lore_embed.py` has any lint warnings, fix them inline. Common likely warnings:
- `UP037` for quoted forward references — none should appear since we used unquoted names with `from __future__ import annotations`.
- `F401` for unused imports — should not occur; every imported name is used at runtime.
- `ARG001` for unused `handler` parameter on `retrieve_for_turn`/`run_worker` — if ruff flags this, suppress with `# noqa: ARG001 — uniform signature for cluster` or, simpler, add a `_ = handler` no-op. Pick the suppression with the smaller diff (likely `noqa`).

- [ ] **Step 6.3: Run formatter**

```bash
just server-fmt
```

Or:
```bash
uv run ruff format .
```

Expected: no changes. If `lore_embed.py` got reformatted, capture the diff and commit it as a separate cosmetic-format commit at Step 6.5.

- [ ] **Step 6.4: Run the full check gate**

```bash
just server-check
```

Expected: lint clean (modulo the two pre-existing warnings) and tests all pass except the pre-existing failures.

- [ ] **Step 6.5: Final commit if formatter made changes**

If `just server-fmt` produced a diff:

```bash
git add -u
git commit -m "refactor(server): apply ruff format to lore_embed.py extraction"
```

Otherwise skip this step.

---

## Mid-flight rebase (if `develop` advances)

Per the handoff's Phase 2 lessons-learned: `develop` may advance while the extraction PR is in flight. If `git fetch origin develop` shows new commits before push:

1. `git fetch origin develop`
2. `git rebase origin/develop`
3. Conflicts will most likely be in import blocks where parallel work added/removed entries adjacent to your changes. Resolution: keep the union of intents (their additions + your removals).
4. After resolving, run `uv run pytest` again — sometimes the parallel work fixes pre-existing failures (Phase 2 hit this with sealed-letter-shared-world-handshake fixing the two `test_confrontation_dispatch_wiring` reds for free).
5. If formatter shows a diff after rebase, fold it into the cleanup commit (don't make a separate commit just for formatting).

---

## Definition of Done — Phase 3

- ✅ `sidequest-server/sidequest/server/dispatch/lore_embed.py` exists with three free functions (`retrieve_for_turn`, `dispatch_worker`, `run_worker`) plus a module-scope `logger = logging.getLogger(__name__)` and the canonical `_watcher_publish` import from `sidequest.telemetry.watcher_hub`.
- ✅ Three thin delegate methods on `WebSocketSessionHandler` route to the new module (`_retrieve_lore_for_turn`, `_dispatch_embed_worker`, `_run_embed_worker`).
- ✅ `tests/server/dispatch/test_lore_embed.py` exists with the skeleton import-existence test (now green) plus three wiring tests (one per delegate) plus the behavioral test for `retrieve_for_turn`'s exception-swallow path.
- ✅ All existing server integration tests pass without modification (especially `test_lore_rag_wiring.py`, which is the canonical end-to-end wiring guard for this cluster).
- ✅ The `embed_task` lifecycle on `_SessionData` is untouched. `cleanup()` (file:792-801) still cancels `sd.embed_task` exactly as before. `test_cleanup_cancels_in_flight_embed_task` passes without modification.
- ✅ `session_handler.py` line count dropped by ~108 lines (from 4693 → ~4585).
- ✅ OTEL `_watcher_publish` count preserved (4 calls moved out of `session_handler.py` and into `lore_embed.py`). Tracer span count preserved (1 span moved). Tracer name preserved verbatim as `"sidequest.server.session_handler"`.
- ✅ `just server-check` passes (modulo the two pre-existing lint warnings and the pre-existing test failure(s) listed in Standing Rules).
- ✅ Four commits land in this order: skeleton, retrieve_for_turn, run_worker, dispatch_worker (plus an optional formatter commit if step 6.5 produced one).

## What This Plan Does NOT Cover

- Phases 4–8 of the spec (media, chargen, small handlers, connect, narration turn). Each gets its own plan after Phase 3 lands.
- Removal of the three thin delegate methods on `WebSocketSessionHandler`. Per the Phase 2 pattern, the delegates stay for the duration of this PR; their removal is an optional post-epic cleanup PR per the handoff.
- Rerouting the production callsites (`session_handler.py:999, 2939, 3816, 3230`) directly to `lore_embed.*` — that is the post-epic cleanup PR. In this PR they continue to route through the thin delegates.
- Renaming the tracer string from `"sidequest.server.session_handler"` to `"sidequest.server.dispatch.lore_embed"`. That is a deliberate non-change — see Task 5 Step 5.3.
- Pre-existing logger debt in `emitters.py` (still imports `logger` from `session_handler`). That is a separate Phase 1 cleanup chore listed in the handoff's outstanding-debt section.
- Any behavioral change. Pure decomposition only.

---

## Self-Review Notes

**Spec coverage check:**
- All three Phase 3 source methods listed in spec → Tasks 2–4 (in dependency order).
- Spec acceptance criteria: ✅ free functions exist (Tasks 2–4), ✅ thin delegates (each Task's "replace body" step), ✅ wiring test per delegate (each Task), ✅ behavioral test (Task 2 step 2.6), ✅ existing integration tests pass (each Task's full-suite step, plus the canonical `test_lore_rag_wiring.py` runs in steps 2.7, 3.6, 4.7), ✅ `embed_task` lifecycle preserved (Task 4 calls out the `_SessionData` attribute is untouched; `cleanup()` block in `session_handler.py:792-801` is not in any task's modified set), ✅ OTEL parity (Task 5), ✅ line-count delta and lint (Task 6).

**Spec drift handled explicitly:**
- `_run_embed_worker` signature: spec said `(handler, sd)`, actual `(handler, sd, pending_count, turn_number)`. Plan uses actual; flagged in Standing Rules.
- Spec line numbers for the source methods drifted ~600 lines after Phases 1+2. Plan uses live grep numbers; flagged in Pre-flight verification.

**Placeholder scan:** No `TBD`, `TODO`, "implement later", or skeleton-only steps. Every code block is complete and copy-pasteable; every command has explicit expected output.

**Type consistency:**
- All three free functions take `handler: WebSocketSessionHandler` as their first positional argument. `handler` is unused in `retrieve_for_turn` and `run_worker` bodies — kept for signature uniformity. Plan calls this out in the "Note on `handler` parameter" callouts and provides a `# noqa: ARG001` suppression option in Task 6 step 6.2 if ruff flags it.
- Function names use the unprefixed forms (`retrieve_for_turn`, `dispatch_worker`, `run_worker`) consistently.
- Delegate names retain their original underscore conventions (`_retrieve_lore_for_turn`, `_dispatch_embed_worker`, `_run_embed_worker`).
- Return types match the original method signatures (`str | None`, `None`, `None`).
- Inter-task references: Task 4's `run_worker(handler, sd, len(pending), turn_number)` call matches Task 3's signature exactly.

**Async-test pattern:** Phase 3 has two async functions (`retrieve_for_turn`, `run_worker`) and one sync function (`dispatch_worker`). The wiring tests use `@pytest.mark.asyncio` for the async ones. The behavioral test in Task 2 step 2.6 demonstrates the "patch the caller's namespace, not the source module" rule for `from-import`-style imports — a common pitfall the implementer should not have to rediscover.

**Subagent prompt rules baked in:** Standing Rules section at the top of this plan repeats the no-`git stash`, do-not-modify-skeleton-test, pre-existing-failures, pinned-cwd, pinned-baseline-SHA, and tracer-name-preservation directives that subagents do not inherit from user memory. Each per-task implementer prompt should re-quote these rules verbatim.

**Known imperfection:** Task 5 OTEL parity uses an exact-equality count rather than `≥` (Phase 1 used `≥`, Phase 2 used `==`). Phase 3 uses `==` because the cluster's OTEL emissions are easy to enumerate (1 span + 4 watcher calls); a strict equality check is the tightest guard available.
