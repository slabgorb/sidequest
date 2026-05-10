# Stateless Narrator Turns — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drop `--resume` from the narrator path. Every turn becomes a stateless, bounded prompt with a system_prompt/user_message split, eliminating context-window growth and the Full/Delta tier machinery.

**Architecture:** Module-level `STABLE_SECTION_NAMES` allowlist + new `PromptRegistry.compose_split()` produces (system, user) string pair. New `ClaudeClient.send_stateless()` invokes `claude -p` without `--resume`. `Orchestrator.process_action()` drops all session-state branching. Spec at `docs/superpowers/specs/2026-05-10-stateless-narrator-design.md`.

**Tech Stack:** Python 3.12 / FastAPI / pydantic v2 / pytest / `claude -p` subprocess CLI / uv.

**Spec reference:** `docs/superpowers/specs/2026-05-10-stateless-narrator-design.md`. ADR-098-in-waiting supersedes ADR-066.

---

## Working directory and commands

All commands run from `/Users/slabgorb/Projects/oq-1/sidequest-server` unless noted otherwise.

- Tests: `uv run pytest <path>::<test> -v`
- Type check: `uv run pyright sidequest/agents/orchestrator.py` (scoped) or `uv run pyright` (full)
- Lint: `uv run ruff check .`
- Full gate: `just check-all` (from orchestrator root `/Users/slabgorb/Projects/oq-1`)

---

## Task 1: Enumerate obsolete tests and confirm caller topology

**Files:**
- Read-only: `tests/agents/`, `sidequest/agents/`, `sidequest/server/`

No code change — produces an enumeration consumed by later tasks.

- [ ] **Step 1: Enumerate tests that pin retired behavior**

Run from `sidequest-server/`:
```bash
grep -rln "NarratorPromptTier\|select_prompt_tier\|rebuild_header\|_recover_from_narrator_failure\|session_established\|session_expired\|warm_reboot" tests/
```

Expected: a list including at minimum `tests/agents/test_orchestrator_session_recovery.py` (647 lines). Write the full list into the commit message of Task 22 ("Delete obsolete tests") — do not delete now.

- [ ] **Step 2: Confirm `send_with_session` callers**

```bash
grep -rln "send_with_session" sidequest/ | grep -v __pycache__
```

Expected callers: `agents/claude_client.py` (definition + protocol), `agents/ollama_client.py` (alternate impl), `agents/orchestrator.py` (narrator), `agents/local_dm.py` (LocalDM preprocessor). Because `local_dm.py` uses the API, **the design's "keep API intact" branch applies** — Task 4 adds a new `send_stateless` method rather than renaming.

- [ ] **Step 3: Confirm `narrator_session_id` references**

```bash
grep -rn "narrator_session_id\|_narrator_session_id" sidequest/
```

Expected: usages in `orchestrator.py`, `server/websocket_session_handler.py:3977`, `server/dispatch/opening.py:448-462`, `server/session_room.py:176` (comment only). Task 23 cleans these up after the orchestrator change lands.

- [ ] **Step 4: Commit the enumeration as a planning note**

No code touched. Skip commit — write findings into your scratchpad / Task 22's commit message later.

---

## Task 2: Add `STABLE_SECTION_NAMES` allowlist + `default_bucket_for_section()` helper

**Files:**
- Create: `sidequest/agents/prompt_framework/bucket.py`
- Create: `tests/agents/test_prompt_framework/test_bucket.py`

- [ ] **Step 1: Write the failing test**

`tests/agents/test_prompt_framework/test_bucket.py`:
```python
"""Tests for the stable-section allowlist that drives system/user split."""

from __future__ import annotations

import pytest

from sidequest.agents.prompt_framework.bucket import (
    STABLE_SECTION_NAMES,
    SectionBucket,
    default_bucket_for_section,
)


def test_known_stable_sections_resolve_to_system():
    """Every name in the allowlist is bucketed as ``system``."""
    for name in STABLE_SECTION_NAMES:
        assert default_bucket_for_section(name) == SectionBucket.System, (
            f"{name!r} is in allowlist but did not resolve to System"
        )


def test_unknown_section_defaults_to_user():
    """A section name not in the allowlist defaults to ``user`` bucket.

    Safer default: dynamic content goes to user message. Stable scaffold
    requires explicit opt-in via the allowlist.
    """
    assert default_bucket_for_section("__never_registered_in_real_code") == SectionBucket.User


def test_allowlist_minimum_contents():
    """Pin the load-bearing stable-scaffold sections (spec §Composition).

    If a section moves out of system bucket, this test breaks loudly so
    the human reviewer sees the regression.
    """
    required = {
        "narrator_identity",
        "narrator_dialogue",
        "soul_principles",
        "output_format",
        "genre_identity",
        "genre_narrator_voice",
        "genre_npc_voice",
        "genre_world_state",
        "narrator_vocabulary",
        "genre_transition_hints",
    }
    missing = required - set(STABLE_SECTION_NAMES)
    assert not missing, f"Required stable sections missing from allowlist: {missing}"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/agents/test_prompt_framework/test_bucket.py -v
```
Expected: FAIL with `ModuleNotFoundError: sidequest.agents.prompt_framework.bucket`.

- [ ] **Step 3: Implement the module**

`sidequest/agents/prompt_framework/bucket.py`:
```python
"""System/user prompt bucketing for stateless narrator turns.

ADR-098 splits the per-turn prompt into a stable scaffold (system_prompt)
and turn-dynamic content (user_message). This module owns the allowlist
that drives the partition; section names not on the allowlist default to
the user bucket.
"""

from __future__ import annotations

from enum import StrEnum


class SectionBucket(StrEnum):
    """Outbound destination for a registered prompt section."""

    System = "system"
    User = "user"


# Section names whose content is byte-identical across every turn of the
# same game given fixed operator settings (genre + verbosity + vocabulary).
# Spec: docs/superpowers/specs/2026-05-10-stateless-narrator-design.md §Composition.
#
# Adding a section here is a load-bearing decision: it must remain stable
# turn-to-turn. If it can change per turn (state, encounter, magic, action,
# recency guardrails), leave it OFF this list — the default is User.
STABLE_SECTION_NAMES: frozenset[str] = frozenset(
    {
        "narrator_identity",
        "narrator_dialogue",
        "soul_principles",
        "output_format",
        "genre_identity",
        "genre_narrator_voice",
        "genre_npc_voice",
        "genre_world_state",
        "narrator_vocabulary",
        "genre_transition_hints",
    }
)


def default_bucket_for_section(name: str) -> SectionBucket:
    """Return the bucket a section name resolves to.

    Names in :data:`STABLE_SECTION_NAMES` go to :attr:`SectionBucket.System`;
    everything else (encounter context, state, recency guardrails, player
    action, etc.) goes to :attr:`SectionBucket.User`.
    """
    if name in STABLE_SECTION_NAMES:
        return SectionBucket.System
    return SectionBucket.User


__all__ = [
    "STABLE_SECTION_NAMES",
    "SectionBucket",
    "default_bucket_for_section",
]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/agents/test_prompt_framework/test_bucket.py -v
```
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/prompt_framework/bucket.py tests/agents/test_prompt_framework/test_bucket.py
git commit -m "feat(prompt): add STABLE_SECTION_NAMES allowlist for system/user split (ADR-098)"
```

---

## Task 3: Add `PromptRegistry.compose_split()` returning (system, user)

**Files:**
- Modify: `sidequest/agents/prompt_framework/core.py` (around line 135, alongside existing `compose()`)
- Test: `tests/agents/test_prompt_framework/test_compose_split.py`

- [ ] **Step 1: Write the failing test**

`tests/agents/test_prompt_framework/test_compose_split.py`:
```python
"""Tests for PromptRegistry.compose_split — the system/user partition."""

from __future__ import annotations

import pytest

from sidequest.agents.prompt_framework.core import PromptRegistry
from sidequest.agents.prompt_framework.types import (
    AttentionZone,
    PromptSection,
    SectionCategory,
)


AGENT = "narrator"


def _section(name: str, content: str, *, zone: AttentionZone = AttentionZone.Valley) -> PromptSection:
    return PromptSection.new(
        name=name,
        content=content,
        zone=zone,
        category=SectionCategory.State,
    )


def test_stable_section_goes_to_system_bucket():
    """A registered section whose name is on the allowlist appears in system_prompt only."""
    registry = PromptRegistry()
    registry.register_section(AGENT, _section("soul_principles", "soul content"))
    registry.register_section(AGENT, _section("player_action", "player text"))

    system, user = registry.compose_split(AGENT)
    assert "soul content" in system
    assert "soul content" not in user
    assert "player text" in user
    assert "player text" not in system


def test_unknown_section_defaults_to_user_bucket():
    """A section name not on the allowlist appears in user_message only."""
    registry = PromptRegistry()
    registry.register_section(AGENT, _section("some_dynamic_thing", "dynamic content"))

    system, user = registry.compose_split(AGENT)
    assert system == ""
    assert "dynamic content" in user


def test_both_buckets_preserve_zone_order():
    """Within each bucket, sections are emitted in zone order (Primacy → Recency)."""
    registry = PromptRegistry()
    registry.register_section(
        AGENT,
        _section("narrator_identity", "IDENTITY-LATE", zone=AttentionZone.Recency),
    )
    registry.register_section(
        AGENT,
        _section("genre_identity", "IDENTITY-EARLY", zone=AttentionZone.Primacy),
    )

    system, _ = registry.compose_split(AGENT)
    assert system.index("IDENTITY-EARLY") < system.index("IDENTITY-LATE")


def test_empty_agent_returns_empty_pair():
    """compose_split on an unknown agent returns ('', '') without error."""
    registry = PromptRegistry()
    system, user = registry.compose_split(AGENT)
    assert (system, user) == ("", "")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/agents/test_prompt_framework/test_compose_split.py -v
```
Expected: FAIL with `AttributeError: 'PromptRegistry' object has no attribute 'compose_split'`.

- [ ] **Step 3: Implement `compose_split`**

In `sidequest/agents/prompt_framework/core.py`, add after the existing `compose()` method (around line 150):

```python
    def compose_split(self, agent_name: str) -> tuple[str, str]:
        """Compose registered sections into a (system_prompt, user_message) pair.

        Partitions sections by :func:`default_bucket_for_section` keyed on
        section name. Within each bucket, sections are emitted in zone
        order (Primacy → Early → Valley → Late → Recency) and joined
        with double-newlines — same shape as :meth:`compose`.

        Used by :class:`Orchestrator` for stateless narrator turns
        (ADR-098). The system prompt carries the stable scaffold; the
        user message carries turn-dynamic state plus the player's action.
        """
        from sidequest.agents.prompt_framework.bucket import (
            SectionBucket,
            default_bucket_for_section,
        )
        from sidequest.telemetry.spans import SPAN_COMPOSE, Span

        with Span.open(SPAN_COMPOSE, {"agent_name": agent_name, "split": True}) as span:
            sections = list(self._sections.get(agent_name, []))
            sections.sort(key=lambda s: s.zone.order())

            system_parts: list[str] = []
            user_parts: list[str] = []
            for s in sections:
                if s.is_empty():
                    continue
                bucket = default_bucket_for_section(s.name)
                if bucket == SectionBucket.System:
                    system_parts.append(s.content)
                else:
                    user_parts.append(s.content)

            system_text = "\n\n".join(system_parts)
            user_text = "\n\n".join(user_parts)
            span.set_attribute("system_chars", len(system_text))
            span.set_attribute("user_chars", len(user_text))
            span.set_attribute("system_section_count", len(system_parts))
            span.set_attribute("user_section_count", len(user_parts))
            return system_text, user_text
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/agents/test_prompt_framework/test_compose_split.py -v
```
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/prompt_framework/core.py tests/agents/test_prompt_framework/test_compose_split.py
git commit -m "feat(prompt): PromptRegistry.compose_split returns (system, user) pair (ADR-098)"
```

---

## Task 4: Add `ClaudeClient.send_stateless`

**Files:**
- Modify: `sidequest/agents/claude_client.py` (add new method on `ClaudeClient` around line 290; also extend the `LlmClient` Protocol at line 758)
- Test: `tests/agents/test_claude_client_stateless.py`

This is a new method, not a refactor of `send_with_session`. `local_dm.py` still uses `send_with_session`, so leave it intact.

- [ ] **Step 1: Write the failing test**

`tests/agents/test_claude_client_stateless.py`:
```python
"""Tests for the stateless send path used by the narrator (ADR-098)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from sidequest.agents.claude_client import ClaudeClient


def _build_client() -> ClaudeClient:
    """Build a client with all subprocess deps mocked at construction."""
    return ClaudeClient()


def test_send_stateless_does_not_pass_resume_or_session_id():
    """The subprocess argv must contain neither --resume nor --session-id.

    The whole point of dropping --resume: no Anthropic session is ever
    referenced or established by this code path.
    """
    client = _build_client()
    captured_args: list[str] = []

    async def fake_run(args, env, span):
        captured_args[:] = list(args)
        return _stub_response()

    with patch.object(ClaudeClient, "_run_subprocess", new=AsyncMock(side_effect=fake_run)):
        asyncio.run(
            client.send_stateless(
                system_prompt="scaffold here",
                user_message="player action here",
                model="opus",
            )
        )

    assert "--resume" not in captured_args
    assert "--session-id" not in captured_args


def test_send_stateless_includes_system_prompt_flag():
    """The stable scaffold rides on --system-prompt; the user message on -p."""
    client = _build_client()
    captured_args: list[str] = []

    async def fake_run(args, env, span):
        captured_args[:] = list(args)
        return _stub_response()

    with patch.object(ClaudeClient, "_run_subprocess", new=AsyncMock(side_effect=fake_run)):
        asyncio.run(
            client.send_stateless(
                system_prompt="SCAFFOLD",
                user_message="USER",
                model="opus",
            )
        )

    assert "--system-prompt" in captured_args
    sys_idx = captured_args.index("--system-prompt")
    assert captured_args[sys_idx + 1] == "SCAFFOLD"
    p_idx = captured_args.index("-p")
    assert captured_args[p_idx + 1] == "USER"


def test_send_stateless_raises_on_empty_user_message():
    """Empty user message is a programmer error, not a stallable turn."""
    from sidequest.agents.claude_client import EmptyResponse

    client = _build_client()
    with pytest.raises(EmptyResponse):
        asyncio.run(
            client.send_stateless(
                system_prompt="anything",
                user_message="   ",
                model="opus",
            )
        )


def _stub_response():
    """Minimal ClaudeResponse-shaped stub for the mocked subprocess path."""
    from sidequest.agents.claude_client import ClaudeResponse

    return ClaudeResponse(text="ok", session_id=None)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/agents/test_claude_client_stateless.py -v
```
Expected: FAIL with `AttributeError: 'ClaudeClient' object has no attribute 'send_stateless'`.

- [ ] **Step 3: Implement `send_stateless`**

In `sidequest/agents/claude_client.py`, after `send_with_session` (line ~340):

```python
    async def send_stateless(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        allowed_tools: list[str] | None = None,
        env_vars: dict[str, str] | None = None,
    ) -> ClaudeResponse:
        """Execute a stateless `claude -p` call (ADR-098).

        Neither `--resume` nor `--session-id` is passed; every call is a
        fresh, independent conversation. The system_prompt carries the
        stable scaffold (identity, voice, format); the user_message
        carries turn-dynamic state plus the player action.

        Unlike :meth:`send_with_session`, the returned
        :attr:`ClaudeResponse.session_id` is not meaningful — callers
        should ignore it.
        """
        allowed = allowed_tools or []
        env = env_vars or {}

        with agent_call_session_span(
            model=model,
            prompt_len=len(user_message),
            backend="claude-cli",
        ) as span:
            if not user_message.strip():
                raise EmptyResponse()

            args: list[str] = ["--model", model]
            if system_prompt:
                args += ["--system-prompt", system_prompt]
            if allowed:
                args.append("--allowedTools")
                args.extend(allowed)
            args += ["-p", user_message, "--output-format", "json"]

            process_env = self._build_env(env)
            return await self._run_subprocess(args, process_env, span)
```

Also extend the `LlmClient` Protocol at the bottom of the file (around line 758):

```python
    async def send_stateless(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        allowed_tools: list[str] | None = None,
        env_vars: dict[str, str] | None = None,
    ) -> ClaudeResponse:
        ...
```

And add a matching `send_stateless` to `ollama_client.py` so the Protocol is satisfied — the simplest implementation concatenates system_prompt and user_message, delegating to the existing Ollama path. (Ollama isn't on the narrator hot path; this is just keeping the Protocol total.)

In `sidequest/agents/ollama_client.py`, after the existing `send_with_session` method:

```python
    async def send_stateless(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        allowed_tools: list[str] | None = None,
        env_vars: dict[str, str] | None = None,
    ) -> ClaudeResponse:
        """Stateless send. Ollama has no native session concept, so we
        compose system_prompt and user_message into a single prompt."""
        combined = f"{system_prompt}\n\n{user_message}" if system_prompt else user_message
        return await self.send_with_session(
            prompt=combined,
            model=model,
            session_id=None,
            system_prompt=None,
            allowed_tools=allowed_tools,
            env_vars=env_vars,
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/agents/test_claude_client_stateless.py -v
uv run pyright sidequest/agents/claude_client.py sidequest/agents/ollama_client.py
```
Expected: 3 PASS, no pyright errors.

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/claude_client.py sidequest/agents/ollama_client.py tests/agents/test_claude_client_stateless.py
git commit -m "feat(claude_client): add send_stateless (no --resume, no session_id) (ADR-098)"
```

---

## Task 5: Drop `tier`/`rebuild_header` params, remove `is_full` gates, gate `opening_scene_constraint` by turn

**Files:**
- Modify: `sidequest/agents/orchestrator.py` (build_narrator_prompt at line 1178, all is_full gates at lines 1224, 1367, 1674, 1705, 1882)

This is the largest single mutation in the plan. It is bounded: rip `is_full` gates, drop two params, re-gate one section.

- [ ] **Step 1: Write a test pinning the new signature and behavior**

Append to `tests/agents/test_narrator_prompt.py` (the existing prompt test file):

```python
async def test_build_narrator_prompt_signature_no_tier_param(simple_turn_context):
    """build_narrator_prompt no longer accepts `tier` or `rebuild_header`.

    ADR-098 removes the Full/Delta tier system. Every turn builds the
    same shape; no per-turn gating beyond turn_number.
    """
    from sidequest.agents.orchestrator import Orchestrator

    orch = Orchestrator()
    # The new signature accepts only (action, context). Calling with
    # `tier=` must fail at the call site (TypeError) and the kwargs-free
    # path must succeed.
    prompt_text, registry = await orch.build_narrator_prompt("test action", simple_turn_context)
    assert isinstance(prompt_text, str)
    assert len(registry.registry(orch._narrator.name())) > 0


async def test_opening_scene_constraint_fires_only_on_turn_zero(
    simple_turn_context, simple_turn_context_turn_three
):
    """Formerly Full-tier-only; now gated by context.turn_number == 0."""
    from sidequest.agents.orchestrator import Orchestrator

    orch = Orchestrator()
    _, registry_t0 = await orch.build_narrator_prompt("hi", simple_turn_context)
    _, registry_t3 = await orch.build_narrator_prompt("hi", simple_turn_context_turn_three)

    names_t0 = {s.name for s in registry_t0.registry(orch._narrator.name())}
    names_t3 = {s.name for s in registry_t3.registry(orch._narrator.name())}
    assert "opening_scene_constraint" in names_t0
    assert "opening_scene_constraint" not in names_t3


async def test_narrator_identity_fires_every_turn(
    simple_turn_context_turn_three,
):
    """Formerly Full-tier-only; now fires unconditionally."""
    from sidequest.agents.orchestrator import Orchestrator

    orch = Orchestrator()
    _, registry = await orch.build_narrator_prompt("hi", simple_turn_context_turn_three)
    names = {s.name for s in registry.registry(orch._narrator.name())}
    assert "narrator_identity" in names
    assert "narrator_dialogue" in names
```

If `simple_turn_context` and `simple_turn_context_turn_three` fixtures don't already exist in `tests/agents/test_narrator_prompt.py` or `conftest.py`, add them. The fixture should produce a minimal `TurnContext` with the genre+character fields populated and `turn_number` set to 0 and 3 respectively. Mirror existing fixtures in the file.

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/agents/test_narrator_prompt.py::test_build_narrator_prompt_signature_no_tier_param -v
```
Expected: FAIL — current signature still requires `tier`, OR the new assertions fail because `narrator_identity` only fires on Full tier.

- [ ] **Step 3: Drop `tier` and `rebuild_header` params from `build_narrator_prompt`**

In `sidequest/agents/orchestrator.py` at line 1178, change the signature:

```python
    async def build_narrator_prompt(
        self,
        action: str,
        context: TurnContext,
    ) -> tuple[str, PromptRegistry]:
```

Inside the function, delete `is_full = tier == NarratorPromptTier.Full` and every `if is_full:` block — taking the inner body unconditionally. Specifically:

- Line ~1222–1238: rebuild_header block (delete entirely; rebuild_header parameter is gone)
- Line ~1224–1261: the `if is_full:` wrapping narrator identity/dialogue/SOUL — unindent its body so all three register unconditionally
- Line ~1367–1411: the `if is_full:` wrapping keeper_monologue/town/chargen/transition_hints — unindent
- Line ~1674: change `if is_full and context.available_sfx:` → `if context.available_sfx:`
- Line ~1705: change `if is_full:` (opening_scene_constraint) → `if context.turn_number == 0:`
- Line ~1882: change `if is_full:` (narrator_vocabulary) → unconditional registration

Remove the `tier=str(tier)` field from the `_pub("prompt_assembled", ...)` payload at ~line 2071. Replace with placeholder fields that Task 17 will populate. For now, just drop the line.

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/agents/test_narrator_prompt.py -v
uv run pyright sidequest/agents/orchestrator.py
```

Expected: new tests PASS. Pyright will flag callers of `build_narrator_prompt` that still pass `tier=` — those are in `process_action` and `_recover_from_narrator_failure`, both addressed in Tasks 6 and 11. **Allow those errors to remain temporarily** — they'll be cleaned in the next two tasks. Note them but proceed.

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/orchestrator.py tests/agents/test_narrator_prompt.py
git commit -m "refactor(narrator): drop tier param + is_full gates from build_narrator_prompt (ADR-098)

Sections formerly gated by Full tier now fire every turn. opening_scene_constraint
re-gated by context.turn_number == 0. Two callers (process_action, recovery path)
still reference tier= and will be cleaned in follow-up tasks."
```

---

## Task 6: Simplify `process_action` — wire `compose_split` + `send_stateless`, drop session machinery

**Files:**
- Modify: `sidequest/agents/orchestrator.py` (`process_action` at line 2479; also affects the streaming twin at line 2117 if present)
- Test: `tests/agents/test_orchestrator_stateless_call.py` (new)

- [ ] **Step 1: Write the failing test** (`test_no_narrator_session_id_in_outbound_call`)

`tests/agents/test_orchestrator_stateless_call.py`:
```python
"""Tests that the narrator path makes stateless outbound calls (ADR-098)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from sidequest.agents.claude_client import ClaudeResponse
from sidequest.agents.orchestrator import Orchestrator


def _fake_response(text: str = '{"narration": "ok"}') -> ClaudeResponse:
    return ClaudeResponse(text=text, session_id=None)


def test_process_action_calls_send_stateless_never_send_with_session(simple_turn_context):
    """Narrator path must never invoke send_with_session — only send_stateless."""
    client = AsyncMock()
    client.send_stateless = AsyncMock(return_value=_fake_response())
    client.send_with_session = AsyncMock(side_effect=AssertionError(
        "send_with_session must not be called from narrator path post-ADR-098"
    ))

    orch = Orchestrator(client=client)
    asyncio.run(orch.process_action("look around", simple_turn_context))

    assert client.send_stateless.call_count == 1
    client.send_with_session.assert_not_called()


def test_send_stateless_call_carries_system_and_user(simple_turn_context):
    """system_prompt is the stable scaffold; user_message contains the player action."""
    client = AsyncMock()
    client.send_stateless = AsyncMock(return_value=_fake_response())

    orch = Orchestrator(client=client)
    asyncio.run(orch.process_action("look around", simple_turn_context))

    call = client.send_stateless.await_args
    assert "system_prompt" in call.kwargs
    assert "user_message" in call.kwargs
    assert "session_id" not in call.kwargs
    # The player's action appears in user_message (via the player_action section).
    assert "look around" in call.kwargs["user_message"]
    # The stable scaffold lives in system_prompt — narrator identity is one
    # of the load-bearing pinned-stable sections.
    assert call.kwargs["system_prompt"] != ""
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/agents/test_orchestrator_stateless_call.py -v
```
Expected: FAIL — `process_action` still uses `send_with_session`.

- [ ] **Step 3: Rewrite `process_action`**

In `sidequest/agents/orchestrator.py`, replace the body of `process_action` (starting line 2479) with the simplified path. The exact code:

```python
    async def process_action(
        self,
        action: str,
        context: TurnContext,
    ) -> NarrationTurnResult:
        """Run one stateless narration turn (ADR-098).

        Build the prompt, partition into (system_prompt, user_message),
        send via :meth:`LlmClient.send_stateless`, parse, return.

        No session id is read or written. No first-turn-vs-subsequent
        branching. If the first attempt fails transiently, retry once;
        otherwise return a degraded :class:`NarrationTurnResult`.
        """
        with orchestrator_process_action_span(action_len=len(action)):
            agent_name = self._narrator.name()

            prompt_text, registry = await self.build_narrator_prompt(action, context)
            system_prompt, user_message = registry.compose_split(agent_name)

            self._maybe_emit_oversized_canary(system_prompt, user_message, registry, agent_name)

            logger.info("narrator.stateless_turn action=%r system_len=%d user_len=%d",
                        action, len(system_prompt), len(user_message))

            response, elapsed_ms = await self._invoke_with_retry_once(
                system_prompt=system_prompt,
                user_message=user_message,
                phase_timings=context.phase_timings,
            )

            if response is None:
                return self._degraded_result(action=action, context=context)

            # Parse + assemble result. The session_id on the response is
            # vestigial post-ADR-098 — ignore it.
            return self._assemble_turn_result(
                response=response,
                prompt_text=prompt_text,
                registry=registry,
                context=context,
                elapsed_ms=elapsed_ms,
                action=action,
            )
```

You will also need three helper methods on `Orchestrator`. Add them above `process_action`:

```python
    async def _invoke_with_retry_once(
        self,
        *,
        system_prompt: str,
        user_message: str,
        phase_timings,
    ) -> tuple[ClaudeResponse | None, int]:
        """Send via send_stateless; retry once on transient failure (ADR-098 §Error handling).

        Returns (response, elapsed_ms). On unrecoverable failure returns
        (None, elapsed_ms) — caller renders the degraded in-fiction stall.
        """
        import time

        with turn_agent_llm_inference_span(
            model=NARRATOR_MODEL,
            prompt_len=len(system_prompt) + len(user_message),
        ):
            for attempt in (1, 2):
                call_start = time.monotonic()
                try:
                    with phase_timings.phase("narrator_subprocess"):
                        response = await self._client.send_stateless(
                            system_prompt=system_prompt,
                            user_message=user_message,
                            model=NARRATOR_MODEL,
                            allowed_tools=[],
                            env_vars={},
                        )
                    elapsed_ms = int((time.monotonic() - call_start) * 1000)
                    return response, elapsed_ms
                except _ClaudeTimeoutError as e:
                    elapsed_ms = int((time.monotonic() - call_start) * 1000)
                    if attempt == 1:
                        logger.warning(
                            "narrator.transient_retry attempt=%d duration_ms=%d error=%s",
                            attempt, elapsed_ms, e,
                        )
                        continue  # retry
                    logger.error("narrator.unrecoverable error=%s after retry", e)
                    return None, elapsed_ms
                except Exception as e:  # noqa: BLE001 - degraded fallback path
                    elapsed_ms = int((time.monotonic() - call_start) * 1000)
                    logger.error("narrator.unrecoverable error=%s", e)
                    return None, elapsed_ms
            return None, 0  # unreachable; keeps type-checker happy

    def _maybe_emit_oversized_canary(
        self,
        system_prompt: str,
        user_message: str,
        registry: PromptRegistry,
        agent_name: str,
    ) -> None:
        """Soft canary for unbounded growth regressions (ADR-098 §Bound canary)."""
        total = len(system_prompt) + len(user_message)
        if total <= SOFT_PROMPT_BUDGET_BYTES:
            return
        from sidequest.telemetry.watcher_hub import publish_event as _pub
        breakdown = [
            {"name": s.name, "chars": len(s.content)}
            for s in registry.registry(agent_name)
        ]
        logger.warning(
            "narrator.prompt_oversized total_bytes=%d budget=%d sections=%d",
            total, SOFT_PROMPT_BUDGET_BYTES, len(breakdown),
        )
        _pub("prompt_oversized", {
            "total_bytes": total,
            "budget": SOFT_PROMPT_BUDGET_BYTES,
            "sections": breakdown,
        }, component="orchestrator")

    def _degraded_result(self, *, action: str, context: TurnContext) -> NarrationTurnResult:
        """Render the in-fiction stall on unrecoverable narrator failure."""
        return NarrationTurnResult(
            narration="The world holds its breath.",
            game_patch=None,
            agent_used=self._narrator.name(),
            session_id=None,
        )

    def _assemble_turn_result(
        self,
        *,
        response: ClaudeResponse,
        prompt_text: str,
        registry: PromptRegistry,
        context: TurnContext,
        elapsed_ms: int,
        action: str,
    ) -> NarrationTurnResult:
        """Parse the narrator response into a NarrationTurnResult.

        Mechanical lift from the pre-refactor process_action body
        (orchestrator.py:2560-2675). The session-id storage block from
        lines 2547-2558 is intentionally NOT lifted — sessions are gone.
        """
        agent_name = self._narrator.name()
        raw_response = response.text
        logger.info(
            "Claude CLI returned narration len=%d duration_ms=%d",
            len(raw_response), elapsed_ms,
        )

        with context.phase_timings.phase("narrator_extraction"):
            extraction = extract_structured_from_response(raw_response)

        prose = extraction["prose"]

        if context.dispatch_package is not None:
            audit_canonical_prose(
                prose=prose,
                package=context.dispatch_package,
                entity_tokens_by_id=self._entity_tokens_for_registry(context),
            )

        if extraction["action_rewrite"] is None:
            logger.warning("action_rewrite absent from extraction — using default (empty rewrite)")

        if extraction["confrontation"]:
            logger.info(
                "encounter.confrontation_initiated confrontation_type=%s",
                extraction["confrontation"],
            )

        for bs_dict in extraction["beat_selections"]:
            if isinstance(bs_dict, dict):
                logger.info(
                    "encounter.agent_beat_selection actor=%s beat_id=%s target=%r",
                    bs_dict.get("actor"), bs_dict.get("beat_id"), bs_dict.get("target"),
                )

        npc_mentions = [NpcMention.from_value(v) for v in extraction["npcs_present"]]
        beat_selections = [
            BeatSelection.from_dict(d)
            for d in extraction["beat_selections"]
            if isinstance(d, dict)
        ]

        visual_scene: VisualScene | None = None
        if extraction["visual_scene"] and isinstance(extraction["visual_scene"], dict):
            visual_scene = VisualScene.from_dict(extraction["visual_scene"])

        action_rewrite: ActionRewrite | None = None
        if isinstance(extraction["action_rewrite"], dict):
            action_rewrite = ActionRewrite.from_dict(extraction["action_rewrite"])

        return NarrationTurnResult(
            narration=prose,
            is_degraded=False,
            location=extraction["location"],
            scene_mood=extraction["scene_mood"],
            visual_scene=visual_scene,
            confrontation=extraction["confrontation"],
            beat_selections=beat_selections,
            npcs_present=npc_mentions,
            items_gained=extraction["items_gained"] if isinstance(extraction["items_gained"], list) else [],
            items_lost=extraction.get("items_lost", []),
            items_discarded=extraction.get("items_discarded", []),
            items_consumed=extraction.get("items_consumed", []),
            footnotes=extraction["footnotes"] if isinstance(extraction["footnotes"], list) else [],
            quest_updates=extraction["quest_updates"] if isinstance(extraction["quest_updates"], dict) else {},
            sfx_triggers=extraction["sfx_triggers"] if isinstance(extraction["sfx_triggers"], list) else [],
            action_rewrite=action_rewrite,
            affinity_progress=extraction["affinity_progress"],
            gold_change=extraction["gold_change"],
            lore_established=extraction["lore_established"],
            status_changes=extraction["status_changes"] if isinstance(extraction["status_changes"], list) else [],
            magic_working=(
                extraction["magic_working"]
                if isinstance(extraction.get("magic_working"), dict)
                else None
            ),
            companions_added=extraction.get("companions_added", []),
            companions_dismissed=extraction.get("companions_dismissed", []),
            game_patch_dict=_extract_game_patch_json(raw_response),
            agent_name=agent_name,
            agent_duration_ms=elapsed_ms,
            token_count_in=response.input_tokens,
            token_count_out=response.output_tokens,
            prompt_tier="",  # vestigial field on NarrationTurnResult; cleanup deferred
            prompt_text=prompt_text,
            raw_response_text=raw_response,
            secret_routes=list(self._last_secret_routes),
        )
```

The body above is the exact post-response logic from the pre-refactor `process_action` (lines 2560-2675), with the session-id storage block (lines 2547-2558) deleted because sessions are gone. The `prompt_tier=""` empty-string is a placeholder for a vestigial field on `NarrationTurnResult` — removing that field is a separate cleanup not in this plan's scope.

Also, define `SOFT_PROMPT_BUDGET_BYTES` near the top of orchestrator.py (above the class definitions) as `SOFT_PROMPT_BUDGET_BYTES = 2_000_000  # ~500K tokens, half of Opus 4.7's 1M window (ADR-098)`.

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/agents/test_orchestrator_stateless_call.py -v
uv run pyright sidequest/agents/orchestrator.py
```

Expected: 2 PASS in the new test. Pyright errors about `_recover_from_narrator_failure` and tier= callers may remain — those are cleaned in Task 11.

- [ ] **Step 5: Run the full orchestrator test suite**

```bash
uv run pytest tests/agents/test_orchestrator.py -v
```

Existing tests that rely on session-state behavior may fail. **Do not fix them here.** Note the failures; they are addressed in Task 22 (obsolete test deletion). Tests of pure prompt content and intent routing should still pass.

- [ ] **Step 6: Commit**

```bash
git add sidequest/agents/orchestrator.py tests/agents/test_orchestrator_stateless_call.py
git commit -m "feat(orchestrator): process_action goes stateless via send_stateless (ADR-098)

Drops session_id read/write, first-turn branching, and the
_recover_from_narrator_failure wrapper. Single retry-once on transient
error; degraded NarrationTurnResult on unrecoverable. Adds prompt
oversized canary."
```

---

## Task 7: `test_prompt_size_bounded_over_session` — the central wiring test

**Files:**
- Test: `tests/agents/test_orchestrator_bounded_prompt.py` (new)

This test proves the central design claim. If it passes, the architecture works.

- [ ] **Step 1: Write the wiring test**

`tests/agents/test_orchestrator_bounded_prompt.py`:
```python
"""ADR-098 central wiring test: prompt size does not grow with turn count."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from sidequest.agents.claude_client import ClaudeResponse
from sidequest.agents.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_prompt_size_bounded_over_30_turns(simple_turn_context):
    """Run 30 simulated turns; assert prompt size does not grow monotonically.

    Acceptance:
      - No strict monotonic increase: there exists at least one N where
        turn[N+1] size <= turn[N] size.
      - max(sizes) / min(sizes) <= 1.5: the largest turn is no more
        than 50% larger than the smallest.

    These two together catch unbounded growth regressions without
    requiring statistical machinery.
    """
    sizes: list[int] = []

    async def capture(system_prompt: str, user_message: str, **kwargs):
        sizes.append(len(system_prompt) + len(user_message))
        return ClaudeResponse(text='{"narration":"ok"}', session_id=None)

    client = AsyncMock()
    client.send_stateless = AsyncMock(side_effect=capture)

    orch = Orchestrator(client=client)
    for turn_n in range(30):
        ctx = replace(simple_turn_context, turn_number=turn_n)
        await orch.process_action(f"turn {turn_n} action", ctx)

    assert len(sizes) == 30

    # Condition 1: not strictly monotonically increasing.
    strictly_growing = all(sizes[i + 1] > sizes[i] for i in range(len(sizes) - 1))
    assert not strictly_growing, (
        f"Prompt size grew on every single turn — strict monotonic growth: {sizes}"
    )

    # Condition 2: bounded range.
    ratio = max(sizes) / min(sizes)
    assert ratio <= 1.5, (
        f"Prompt size range too wide: max={max(sizes)} min={min(sizes)} ratio={ratio:.2f}"
    )
```

`TurnContext` is a `@dataclass` (confirmed at `orchestrator.py:355`), so `dataclasses.replace(simple_turn_context, ...)` is the correct mutation pattern. The `simple_turn_context` fixture should produce a `TurnContext` instance with semantically-constant state (no growing collections) so the wiring test isolates the framework's contribution, not the per-turn state growth that story 23-4 addresses.

- [ ] **Step 2: Run test to verify it passes**

```bash
uv run pytest tests/agents/test_orchestrator_bounded_prompt.py -v
```

Expected: PASS. If it fails, a registered section is accumulating state across `simple_turn_context` invocations — that's a real bug the test is meant to catch. The test fixture must produce semantically-similar contexts; a context whose `npc_pool` grows turn-to-turn would legitimately fail this test (and indicate the location-scoping work, story 23-4, is needed). For Task 7, the fixture should hold state size constant.

- [ ] **Step 3: Commit**

```bash
git add tests/agents/test_orchestrator_bounded_prompt.py
git commit -m "test(narrator): wiring test — prompt size bounded over 30-turn session (ADR-098)"
```

---

## Task 8: `test_system_prompt_stable_within_session`

**Files:**
- Test: `tests/agents/test_orchestrator_system_stable.py` (new)

- [ ] **Step 1: Write the test**

`tests/agents/test_orchestrator_system_stable.py`:
```python
"""ADR-098: system_prompt is byte-identical across turns of one game."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from sidequest.agents.claude_client import ClaudeResponse
from sidequest.agents.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_system_prompt_identical_across_10_turns(simple_turn_context):
    captured_system: list[str] = []

    async def capture(system_prompt: str, user_message: str, **kwargs):
        captured_system.append(system_prompt)
        return ClaudeResponse(text='{"narration":"ok"}', session_id=None)

    client = AsyncMock()
    client.send_stateless = AsyncMock(side_effect=capture)

    orch = Orchestrator(client=client)
    for turn_n in range(10):
        ctx = replace(simple_turn_context, turn_number=turn_n)
        await orch.process_action(f"turn {turn_n} action", ctx)

    distinct = set(captured_system)
    assert len(distinct) == 1, (
        f"system_prompt should be byte-identical across all 10 turns; "
        f"got {len(distinct)} distinct values"
    )
```

- [ ] **Step 2: Run test to verify it passes**

```bash
uv run pytest tests/agents/test_orchestrator_system_stable.py -v
```
Expected: PASS.

If it fails: a section name in `STABLE_SECTION_NAMES` is producing content that varies turn-to-turn (a category mistake). The test names the regression.

- [ ] **Step 3: Commit**

```bash
git add tests/agents/test_orchestrator_system_stable.py
git commit -m "test(narrator): system_prompt byte-identical across same-session turns (ADR-098)"
```

---

## Task 9: `test_system_user_split_categories` — enforce the allowlist

**Files:**
- Test: `tests/agents/test_orchestrator_split_allowlist.py` (new)

- [ ] **Step 1: Write the test**

`tests/agents/test_orchestrator_split_allowlist.py`:
```python
"""ADR-098: every registered section name must be on the allowlist or default to user."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from sidequest.agents.claude_client import ClaudeResponse
from sidequest.agents.orchestrator import Orchestrator
from sidequest.agents.prompt_framework.bucket import (
    STABLE_SECTION_NAMES,
    SectionBucket,
    default_bucket_for_section,
)


@pytest.mark.asyncio
async def test_all_registered_sections_have_deterministic_bucket(simple_turn_context):
    """For a representative turn, every registered section is bucketed without surprise.

    No section should resolve to a bucket that contradicts its semantic
    role. Stable sections (identity, voice, format) → system. Dynamic
    sections (state, action, guardrail) → user. The test verifies the
    allowlist isn't drifting from reality.
    """
    client = AsyncMock()
    client.send_stateless = AsyncMock(return_value=ClaudeResponse(text='{"narration":"ok"}', session_id=None))
    orch = Orchestrator(client=client)

    _, registry = await orch.build_narrator_prompt("look around", simple_turn_context)
    section_names = {s.name for s in registry.registry(orch._narrator.name())}

    # Pinned: at least one stable section must be present (else allowlist
    # has drifted out of sync with the registrars).
    pinned = section_names & STABLE_SECTION_NAMES
    assert pinned, (
        f"None of STABLE_SECTION_NAMES appeared in the prompt for a basic turn; "
        f"registered: {sorted(section_names)}; allowlist: {sorted(STABLE_SECTION_NAMES)}"
    )

    # Every section name has a defined bucket (this is trivially true via
    # the helper, but pinning it documents the contract).
    for name in section_names:
        bucket = default_bucket_for_section(name)
        assert bucket in (SectionBucket.System, SectionBucket.User)


@pytest.mark.asyncio
async def test_known_dynamic_sections_default_to_user(simple_turn_context):
    """Spot-check: player_action, game_state, npc_roster must NOT be in system bucket."""
    client = AsyncMock()
    client.send_stateless = AsyncMock(return_value=ClaudeResponse(text='{"narration":"ok"}', session_id=None))
    orch = Orchestrator(client=client)

    captured: dict[str, str] = {}

    async def capture(system_prompt: str, user_message: str, **kwargs):
        captured["system"] = system_prompt
        captured["user"] = user_message
        return ClaudeResponse(text='{"narration":"ok"}', session_id=None)

    client.send_stateless.side_effect = capture
    await orch.process_action("look around", simple_turn_context)

    # The player's action text must appear in user_message, not system_prompt.
    assert "look around" in captured["user"]
    assert "look around" not in captured["system"]
```

- [ ] **Step 2: Run test to verify it passes**

```bash
uv run pytest tests/agents/test_orchestrator_split_allowlist.py -v
```
Expected: 2 PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/agents/test_orchestrator_split_allowlist.py
git commit -m "test(narrator): every registered section has a deterministic bucket (ADR-098)"
```

---

## Task 10: `test_merged_player_actions_stateless` — MP turns work without session

**Files:**
- Test: `tests/agents/test_orchestrator_mp_stateless.py` (new)

- [ ] **Step 1: Write the test**

`tests/agents/test_orchestrator_mp_stateless.py`:
```python
"""ADR-098: MP merged turns run stateless, same path as single-PC turns."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from sidequest.agents.claude_client import ClaudeResponse
from sidequest.agents.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_mp_merged_turn_is_stateless(simple_turn_context):
    """A merged turn renders multi-PC declarations into user_message; no session reads/writes."""
    ctx = replace(
        simple_turn_context,
        merged_player_actions=[
            ("Laverne", "I look at Shirley."),
            ("Shirley", "I look back."),
            ("Lenny", "I check the door."),
        ],
    )

    client = AsyncMock()
    captured: dict[str, str] = {}

    async def capture(system_prompt: str, user_message: str, **kwargs):
        captured["system"] = system_prompt
        captured["user"] = user_message
        # session_id should NOT appear in kwargs
        assert "session_id" not in kwargs
        return ClaudeResponse(text='{"narration":"ok"}', session_id=None)

    client.send_stateless = AsyncMock(side_effect=capture)
    client.send_with_session = AsyncMock(side_effect=AssertionError("must not be called"))

    orch = Orchestrator(client=client)
    result = await orch.process_action("(ignored in MP path)", ctx)

    # Each declaration appears in the user message.
    assert "Laverne" in captured["user"]
    assert "Shirley" in captured["user"]
    assert "Lenny" in captured["user"]
    assert result.narration  # non-empty
```

- [ ] **Step 2: Run test to verify it passes**

```bash
uv run pytest tests/agents/test_orchestrator_mp_stateless.py -v
```
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/agents/test_orchestrator_mp_stateless.py
git commit -m "test(narrator): MP merged turn runs stateless (ADR-098)"
```

---

## Task 11: `test_transient_retry_once` + delete recovery scaffolding

**Files:**
- Modify: `sidequest/agents/orchestrator.py` (delete `_classify_narrator_error`, `_narrator_error_signature`, `_compose_rebuild_header`, `_recover_from_narrator_failure` — lines 917–1105)
- Test: `tests/agents/test_orchestrator_retry.py` (new)

- [ ] **Step 1: Write the test**

`tests/agents/test_orchestrator_retry.py`:
```python
"""ADR-098: transient retry-once; otherwise degraded result."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from sidequest.agents.claude_client import ClaudeResponse, _ClaudeTimeoutError
from sidequest.agents.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_transient_failure_retries_once_then_succeeds(simple_turn_context):
    """One _ClaudeTimeoutError on first call → retry → success on second."""
    client = AsyncMock()
    call_count = {"n": 0}

    async def flaky(system_prompt, user_message, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise _ClaudeTimeoutError("transient")
        return ClaudeResponse(text='{"narration":"ok"}', session_id=None)

    client.send_stateless = AsyncMock(side_effect=flaky)
    orch = Orchestrator(client=client)

    result = await orch.process_action("look", simple_turn_context)
    assert call_count["n"] == 2
    assert result.narration  # non-empty success


@pytest.mark.asyncio
async def test_double_transient_returns_degraded_result(simple_turn_context):
    """Two _ClaudeTimeoutError in a row → degraded in-fiction stall, no third call."""
    client = AsyncMock()
    call_count = {"n": 0}

    async def always_flaky(system_prompt, user_message, **kwargs):
        call_count["n"] += 1
        raise _ClaudeTimeoutError("persistent")

    client.send_stateless = AsyncMock(side_effect=always_flaky)
    orch = Orchestrator(client=client)

    result = await orch.process_action("look", simple_turn_context)
    assert call_count["n"] == 2  # not 3 — no exponential retry
    assert "world holds its breath" in result.narration.lower()
```

- [ ] **Step 2: Run test to verify it passes**

The retry behavior was already implemented in Task 6 via `_invoke_with_retry_once`. Run:

```bash
uv run pytest tests/agents/test_orchestrator_retry.py -v
```
Expected: 2 PASS.

- [ ] **Step 3: Delete the recovery scaffolding**

In `sidequest/agents/orchestrator.py`, delete these methods entirely (lines 917–1105 in the pre-refactor file):
- `_classify_narrator_error`
- `_narrator_error_signature`
- `_compose_rebuild_header`
- `_recover_from_narrator_failure`

Also delete the `recap_provider` parameter from `Orchestrator.__init__` (line ~850) and the corresponding `self._recap_provider` field assignment. Callers that pass `recap_provider=` will need updating in Task 23.

- [ ] **Step 4: Verify type-check + retry test still passes**

```bash
uv run pyright sidequest/agents/orchestrator.py
uv run pytest tests/agents/test_orchestrator_retry.py -v
```
Expected: pyright clean (or only stragglers from Task 23 cleanup callers); retry test PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/orchestrator.py tests/agents/test_orchestrator_retry.py
git commit -m "refactor(orchestrator): retry-once + delete ADR-066 §8 recovery scaffolding (ADR-098)

~155 lines removed. _recover_from_narrator_failure, _classify_narrator_error,
_narrator_error_signature, _compose_rebuild_header all gone. recap_provider
field dropped from Orchestrator.__init__."
```

---

## Task 12: `test_oversized_prompt_canary` — canary fires + turn continues

**Files:**
- Test: `tests/agents/test_orchestrator_oversized_canary.py` (new)

The canary itself was implemented in Task 6 via `_maybe_emit_oversized_canary`. This task pins it under test.

- [ ] **Step 1: Write the test**

`tests/agents/test_orchestrator_oversized_canary.py`:
```python
"""ADR-098: oversized prompt logs a warning + emits OTEL but does not fail the turn."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from unittest.mock import AsyncMock, patch

import pytest

from sidequest.agents.claude_client import ClaudeResponse
from sidequest.agents.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_oversized_prompt_warns_but_completes(simple_turn_context, caplog):
    """Force the budget below realistic prompt size; assert warning + completion."""
    client = AsyncMock()
    client.send_stateless = AsyncMock(
        return_value=ClaudeResponse(text='{"narration":"ok"}', session_id=None)
    )

    orch = Orchestrator(client=client)
    # Patch SOFT_PROMPT_BUDGET_BYTES to a tiny value so any real turn overflows it.
    with patch("sidequest.agents.orchestrator.SOFT_PROMPT_BUDGET_BYTES", 10):
        with caplog.at_level(logging.WARNING, logger="sidequest.agents.orchestrator"):
            result = await orch.process_action("look", simple_turn_context)

    # Turn still completed.
    assert result.narration

    # Canary warning fired.
    assert any(
        "narrator.prompt_oversized" in r.message for r in caplog.records
    ), f"oversized canary did not fire; caplog: {[r.message for r in caplog.records]}"


@pytest.mark.asyncio
async def test_normal_prompt_no_canary(simple_turn_context, caplog):
    """At normal size, no canary warning fires."""
    client = AsyncMock()
    client.send_stateless = AsyncMock(
        return_value=ClaudeResponse(text='{"narration":"ok"}', session_id=None)
    )

    orch = Orchestrator(client=client)
    with caplog.at_level(logging.WARNING, logger="sidequest.agents.orchestrator"):
        await orch.process_action("look", simple_turn_context)

    assert not any(
        "narrator.prompt_oversized" in r.message for r in caplog.records
    )
```

- [ ] **Step 2: Run test to verify it passes**

```bash
uv run pytest tests/agents/test_orchestrator_oversized_canary.py -v
```
Expected: 2 PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/agents/test_orchestrator_oversized_canary.py
git commit -m "test(narrator): oversized-prompt canary fires but does not fail turn (ADR-098)"
```

---

## Task 13: Delete `NarratorPromptTier`, `select_prompt_tier`, session-id machinery

**Files:**
- Modify: `sidequest/agents/orchestrator.py` (delete class + methods + fields)

- [ ] **Step 1: Delete the tier enum and selector**

Remove from `sidequest/agents/orchestrator.py`:
- `class NarratorPromptTier:` (lines 83–94)
- `def select_prompt_tier(self, context: TurnContext) -> str:` (lines 1146–1172)
- `def reset_narrator_session(self) -> None:` (lines 897–906)
- `def set_narrator_session_id(self, session_id: str) -> None:` (lines 908–911)

- [ ] **Step 2: Delete the session-state fields**

In `Orchestrator.__init__` (line ~846), remove these field assignments:
- `self._narrator_session_id: str | None = None`
- `self._session_genre: str | None = None`
- `self._session_lock: Lock = Lock()`

Remove the `Lock` import if no longer used.

Remove any remaining references to `self._narrator_session_id` / `self._session_genre` / `self._session_lock` in the file.

- [ ] **Step 3: Run typecheck + agents tests**

```bash
uv run pyright sidequest/agents/orchestrator.py
uv run pytest tests/agents/test_orchestrator_stateless_call.py tests/agents/test_orchestrator_bounded_prompt.py tests/agents/test_orchestrator_retry.py -v
```

Expected: pyright clean for the file itself. External callers (in `server/`) that still reference `_narrator_session_id` are addressed in Task 23. Suppress those by checking the file path of any errors — they should all be in `sidequest/server/`.

- [ ] **Step 4: Commit**

```bash
git add sidequest/agents/orchestrator.py
git commit -m "refactor(orchestrator): delete NarratorPromptTier, select_prompt_tier, session state (ADR-098)

NarratorPromptTier enum, select_prompt_tier, reset_narrator_session,
set_narrator_session_id all gone. _narrator_session_id, _session_genre,
_session_lock fields removed from Orchestrator."
```

---

## Task 14: Update `prompt_assembled` OTEL payload (system_len, user_len, bounded)

**Files:**
- Modify: `sidequest/agents/orchestrator.py` (`build_narrator_prompt` publish call around line 2062)

- [ ] **Step 1: Write the test**

Append to `tests/agents/test_prompt_zones_dashboard.py` (existing file):
```python
@pytest.mark.asyncio
async def test_prompt_assembled_event_has_split_fields(simple_turn_context):
    """ADR-098: prompt_assembled carries system_len, user_len, bounded; no tier."""
    from sidequest.agents.orchestrator import Orchestrator
    from sidequest.telemetry.watcher_hub import subscribe

    events: list[dict] = []

    def collect(evt_type, payload, component):
        if evt_type == "prompt_assembled":
            events.append(payload)

    # Subscribe to the watcher hub for the duration of the test.
    # Adjust to match the actual subscribe API in watcher_hub.
    with subscribe(collect):
        orch = Orchestrator()
        await orch.build_narrator_prompt("look", simple_turn_context)

    assert events, "no prompt_assembled event published"
    payload = events[-1]
    assert "system_len" in payload
    assert "user_len" in payload
    assert payload.get("bounded") is True
    assert "tier" not in payload
```

If the `subscribe` API differs, adapt to the actual hub interface (the test should subscribe before, snapshot events, unsubscribe).

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/agents/test_prompt_zones_dashboard.py::test_prompt_assembled_event_has_split_fields -v
```
Expected: FAIL — current payload has `tier=str(tier)` (now broken from Task 5, may already be missing) and lacks the split fields.

- [ ] **Step 3: Update the publish call**

In `build_narrator_prompt`, the `_pub("prompt_assembled", ...)` call around line 2062. Replace its payload dict with:

```python
            # Compute split for telemetry payload — actual send-time
            # split happens in process_action via compose_split.
            from sidequest.agents.prompt_framework.bucket import (
                SectionBucket,
                default_bucket_for_section,
            )
            system_chars = sum(
                len(s.content) for s in sections
                if not s.is_empty()
                and default_bucket_for_section(s.name) == SectionBucket.System
            )
            user_chars = sum(
                len(s.content) for s in sections
                if not s.is_empty()
                and default_bucket_for_section(s.name) == SectionBucket.User
            )

            _pub(
                "prompt_assembled",
                {
                    "agent_name": agent_name,
                    "agent": agent_name,
                    "turn_number": context.turn_number,
                    "section_count": section_count,
                    "prompt_len": len(prompt_text),
                    "system_len": system_chars,
                    "user_len": user_chars,
                    "bounded": True,
                    "total_tokens": max(1, len(prompt_text) // 4),
                    "zones": zones_payload,
                },
                component="prompt_builder",
            )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/agents/test_prompt_zones_dashboard.py -v
```
Expected: PASS (the new test and any pre-existing ones not relying on `tier`).

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/orchestrator.py tests/agents/test_prompt_zones_dashboard.py
git commit -m "feat(otel): prompt_assembled adds system_len/user_len/bounded, removes tier (ADR-098)"
```

---

## Task 15: Drop `narrator_session_id` from save schema

**Files:**
- Modify: `sidequest/game/persistence.py` (or wherever the save model lives — grep first)

- [ ] **Step 1: Locate the save model**

```bash
grep -rn "narrator_session_id" sidequest/game/ | head
```

Find the field declaration on the save/persistence pydantic model. If the field is on a pydantic `BaseModel` subclass, removing it cleanly requires `model_config = {"extra": "ignore"}` on that model so old saves with the field set load without error.

- [ ] **Step 2: Write the test**

`tests/game/test_save_load_legacy_session_id.py`:
```python
"""ADR-098: saves carrying legacy narrator_session_id load with the field ignored."""

from __future__ import annotations

import pytest


def test_legacy_save_with_narrator_session_id_loads():
    """A save dict containing narrator_session_id deserializes without error.

    Per spec — saves are exploratory; no migration script. The model
    must tolerate the extra field on load.
    """
    from sidequest.game.persistence import SaveModel  # adjust to actual name

    legacy_payload = {
        # ...minimal valid save fields...
        "narrator_session_id": "abc-123-legacy",  # extra field from old saves
    }
    # Fill in the minimum required fields for SaveModel construction;
    # the assertion is that this raises no validation error.
    save = SaveModel.model_validate(legacy_payload)
    assert save is not None
    # The field must NOT round-trip back into the model.
    assert not hasattr(save, "narrator_session_id")
```

The fixture needs to know `SaveModel`'s exact required fields. Inspect the file from Step 1 to fill in the minimum-valid payload.

- [ ] **Step 3: Run test to verify it fails or already passes**

```bash
uv run pytest tests/game/test_save_load_legacy_session_id.py -v
```

If the save model already uses `extra="ignore"`, the test passes immediately. If it uses `extra="forbid"`, the test fails — proceed to Step 4.

- [ ] **Step 4: Update the save model**

Remove the `narrator_session_id` field declaration. Set `model_config = {"extra": "ignore"}` on the save model class. Save and re-run the test.

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/persistence.py tests/game/test_save_load_legacy_session_id.py
git commit -m "refactor(save): drop narrator_session_id field, ignore on legacy loads (ADR-098)"
```

---

## Task 16: Clean up server-side `narrator_session_id` references

**Files:**
- Modify: `sidequest/server/websocket_session_handler.py:3977`
- Modify: `sidequest/server/dispatch/opening.py:448,462`
- Modify: `sidequest/server/session_room.py:176` (comment only)

- [ ] **Step 1: Locate and clean each reference**

For `websocket_session_handler.py:3977`:
```python
# OLD:
narrator_session_id=getattr(sd.orchestrator, "_narrator_session_id", None)
# REMOVE the kwarg from the function call entirely.
```

For `dispatch/opening.py:448`:
```python
# OLD signature:
def emit_opening_meta(... narrator_session_id: str, ...):
# REMOVE the narrator_session_id parameter and any payload entries that
# reference it (line 462: "narrator_session_id": narrator_session_id).
```

For `session_room.py:176`:
```python
# OLD comment:
# share one Claude --resume session, one ``_narrator_session_id``,
# UPDATE to reflect stateless turns post-ADR-098.
```

- [ ] **Step 2: Run full server test suite**

```bash
uv run pytest tests/ -v --ignore=tests/agents/test_orchestrator_session_recovery.py
```

Expected: any failures should be in test files Task 22 will delete. Pure server tests pass.

- [ ] **Step 3: Commit**

```bash
git add sidequest/server/
git commit -m "refactor(server): remove narrator_session_id passthrough from handlers (ADR-098)"
```

---

## Task 17: Delete obsolete tests + handler `recap_provider` callers

**Files:**
- Delete: `tests/agents/test_orchestrator_session_recovery.py` (647 lines, entirely tests retired §8 recovery)
- Modify: any test method elsewhere that references `PromptTier`, `select_prompt_tier`, `rebuild_header`, `session_established`, `session_expired`, `warm_reboot`
- Modify: any production caller of `Orchestrator(... recap_provider=...)` to drop the kwarg

- [ ] **Step 1: Re-run the enumeration from Task 1 to confirm scope**

```bash
grep -rln "NarratorPromptTier\|select_prompt_tier\|rebuild_header\|_recover_from_narrator_failure\|session_established\|session_expired\|warm_reboot" tests/ sidequest/
```

- [ ] **Step 2: Delete the recovery test file**

```bash
git rm tests/agents/test_orchestrator_session_recovery.py
```

- [ ] **Step 3: Triage other matches**

For each remaining match: if the test asserts on retired behavior (tier selection, rebuild header content, ADR-066 §8 retry classification), delete that test method. If a production file imports `NarratorPromptTier`, remove the import. If a production caller passes `recap_provider=`, drop the kwarg.

- [ ] **Step 4: Run the full server test suite**

```bash
uv run pytest tests/ -v
uv run pyright sidequest/
```

Expected: all green. If pyright flags anything, fix the import or call site. Tests that legitimately fail at this stage indicate a regression in the new code — investigate before continuing.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "test/refactor: delete obsolete ADR-066 §8 recovery + tier-selection tests (ADR-098)

- tests/agents/test_orchestrator_session_recovery.py deleted (647 lines)
- Stragglers in tests/ and sidequest/ updated to match new stateless contract
- All retired imports and kwargs cleaned"
```

---

## Task 18: Update sidequest-ui dashboard consumer for new payload shape

**Files:**
- Modify: `sidequest-ui/src/components/Dashboard/` or wherever the Prompt tab consumes `prompt_assembled` (grep to locate)

Cross-repo PR territory — coordinate landing with the server change.

- [ ] **Step 1: Locate the dashboard consumer**

From `/Users/slabgorb/Projects/oq-1`:
```bash
grep -rn "prompt_assembled\|prompt_tier\|tier:" sidequest-ui/src/ | grep -v node_modules | head -20
```

- [ ] **Step 2: Update the TypeScript type and renderer**

The payload's `tier` field is gone; replace any UI that displays it with the new `bounded: boolean` + `system_len: number` + `user_len: number` fields. Show a system/user split chart in the Prompt tab in place of the tier badge.

Exact UI shape is a UX call — keep the change minimal: replace the tier text with "stateless · bounded" and add the system/user bytes alongside `total_tokens`.

- [ ] **Step 3: Run UI tests**

From `/Users/slabgorb/Projects/oq-1/sidequest-ui`:
```bash
npx vitest run
npx tsc --noEmit
```

Expected: green. Any consumer of the old `tier` field on the payload type must be removed.

- [ ] **Step 4: Commit**

```bash
git add sidequest-ui/
git commit -m "feat(dashboard): prompt tab shows system/user split + bounded marker (ADR-098)"
```

---

## Task 19: Write ADR-098

**Files:**
- Create: `docs/adr/098-stateless-narrator-turns.md`

- [ ] **Step 1: Author ADR-098**

Use the existing ADR format. Cribbed straight from the spec; structure:

```markdown
---
id: 98
title: Stateless Narrator Turns — Drop --resume, Bounded Per-Turn Prompts
status: accepted
status_rationale: "Brainstorm + spec + plan completed; supersedes ADR-066 which proved load-bearing in the opposite direction over long sessions."
date: 2026-05-10
supersedes: [66]
related: [67, 23-4]
---

## Context
[Lift from spec §Problem]

## Decision
[Lift from spec §Decision]

## Consequences
[Lift the property triplet from §Decision: bounded cost, no crashes, complete OTEL]

## Implementation
See plan: `docs/superpowers/plans/2026-05-10-stateless-narrator.md`
```

The frontmatter schema is in ADR-088. Validate format by checking an existing recent ADR (e.g. `096`) for exact field shapes.

- [ ] **Step 2: Mark ADR-066 superseded**

In `docs/adr/066-persistent-opus-narrator-sessions.md`, update frontmatter:
```yaml
status: superseded
status_rationale: "Replaced by ADR-098 — session memory was causing the very latency it was introduced to solve; long sessions ran into context_window_full."
superseded_by: 98
```

- [ ] **Step 3: Update auto-generated indexes**

From `/Users/slabgorb/Projects/oq-1`:
```bash
python scripts/regenerate_adr_indexes.py
```

This rewrites `docs/adr/README.md` (per ADR-088). Inspect the diff — the load-bearing reads section + SUPERSEDED.md should both reflect the change.

- [ ] **Step 4: Update ADR-067 §session-management text**

In `docs/adr/067-unified-narrator-agent.md`, find any prose that references `--resume`, "persistent session", "session continuation", warm-reboot. Replace with the stateless-turn shape. The unified-agent decision (one agent, multiple intents) is unchanged.

- [ ] **Step 5: Commit**

```bash
git add docs/adr/098-stateless-narrator-turns.md docs/adr/066-persistent-opus-narrator-sessions.md docs/adr/067-unified-narrator-agent.md docs/adr/README.md docs/adr/SUPERSEDED.md
git commit -m "docs(adr): ADR-098 stateless narrator turns; supersedes ADR-066"
```

---

## Task 20: Run the full quality gate

**Files:** none (verification only)

- [ ] **Step 1: Run check-all from orchestrator root**

From `/Users/slabgorb/Projects/oq-1`:
```bash
just check-all
```

This runs `server-check` (ruff + pytest), `client-lint`, `client-test`, `daemon-lint`, and `client-typecheck`. All must be green.

- [ ] **Step 2: Smoke-test the running stack**

```bash
just up
```

Open `http://localhost:5173`. Start a fresh game, take 5 turns. In the GM dashboard's Prompt tab, confirm the new `system/user` split appears and there is no `tier` badge.

- [ ] **Step 3: Watch the logs for the canary**

```bash
just logs server | grep narrator
```

Expected lines:
- `narrator.stateless_turn action=... system_len=... user_len=...` on every turn
- No `narrator.session_establish` or `narrator.session_resume` (those lived in `send_with_session`)
- No `narrator.prompt_oversized` (normal sessions don't trip the canary)

- [ ] **Step 4: Tear down**

```bash
just down
```

- [ ] **Step 5: Final commit (if any tweaks landed during smoke test)**

```bash
git status
# If clean, no commit needed. If you tweaked anything during smoke,
# commit it with a descriptive message.
```

---

## Self-review (for the implementing engineer)

Before opening the PR:

1. **Spec coverage:** every requirement in `docs/superpowers/specs/2026-05-10-stateless-narrator-design.md` maps to a task. Re-read the spec and confirm.
2. **All seven named tests exist** (search the test files):
   - `test_prompt_size_bounded_over_session` (Task 7)
   - `test_system_prompt_stable_within_session` (Task 8)
   - `test_system_user_split_categories` (Task 9 — the test asserting allowlist semantics)
   - `test_no_narrator_session_id_in_outbound_call` (Task 6)
   - `test_oversized_prompt_canary` (Task 12)
   - `test_merged_player_actions_stateless` (Task 10)
   - `test_transient_retry_once` (Task 11)
3. **No `NarratorPromptTier`, `select_prompt_tier`, `--resume`, `_recover_from_narrator_failure` remain in `sidequest/`** (grep should return empty).
4. **`local_dm.py` and `ollama_client.py` still compile and pass tests** — they keep `send_with_session`.
5. **Type-check is clean:** `uv run pyright` returns zero errors.
