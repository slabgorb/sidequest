# Local DM — Group B: Decomposer MVP (Phase A, Haiku) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a server-side `LocalDM` decomposer that runs between sealed-letter completion and narrator invocation, producing a `DispatchPackage` that (a) resolves referents, (b) fires three initial subsystem dispatches (`reflect_absence`, `distinctive_detail_hint`, `npc_agency`), and (c) injects narrator directives into the existing `<game_state>` prompt block. Haiku-backed, structurally ready for Phase B local fine-tune swap.

**Architecture:** One new phase slots into the already-defined `TurnPhase.IntentRouting` (created but unused in `game/turn.py`). The decomposer is a `claude -p --model haiku --resume` call, following ADR-066 persistent-session pattern (same shape as the narrator, different session id). The decomposer emits structured JSON only — never prose — so it is immune to the `claude -p` tool-skip failure mode described in ADR-059. `DispatchPackage` types live in `sidequest/protocol/`. The `LocalDM` class lives in `sidequest/agents/local_dm.py`. Subsystem implementations live in `sidequest/agents/subsystems/`. Session handler calls the decomposer before the narrator and threads the `DispatchPackage` through `TurnContext` into the narrator prompt registry as a new `narrator_directives` prompt section. Every dispatch emits OTEL spans.

**Tech Stack:** Python 3.11+, pydantic (protocol types), pytest + pytest-asyncio, uv (server). `claude -p` subprocess via existing `ClaudeClient`. OpenTelemetry spans via existing `tracer()` singleton. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md` — §3 (architecture), §4 (lethality — stubs only in Group B), §5 (DispatchPackage contract), §6 (per-turn flow), §7 Phase A (Haiku deployment), §10 Story Group B.

**Repos touched:**
- `sidequest-server/` — all work (branch: `feat/local-dm-group-b`, targets `develop`)

No UI or daemon changes in Group B. GM panel visibility work is acknowledged in Task 14 as an OTEL emission prerequisite; the UI tab consuming those spans is deferred to Group C (lethality arbitration) when there's mechanical content worth watching.

---

## Roadmap Context (Groups C–G)

This plan is Group B of seven. Prior group is shipped:

- **Group A (shipped)** — Dead-code demolition. Removed `action_flags`, `classified_intent = "exploration"`, `preprocessor.py`. Freed `TurnPhase.IntentRouting` for reuse.
- **Group B (this plan)** — Decomposer MVP (Haiku, three subsystems, narrator directive injection).
- **Group C** — Lethality arbitration + `LethalityVerdict` + genre-pack `lethality_policy`. Extends B.
- **Group D** — Corpus miner + per-player save diff + standalone labeling tool. Can run parallel to C.
- **Group E** — `LlmClient` trait + Ollama/MLX backends + QLoRA fine-tune (ADR-073 Phases 1–3). Depends on D corpus.
- **Group F** — Specialization (per-genre LoRA, per-player tuning, in-game feedback). Optional.
- **Group G (LOAD-BEARING for multiplayer)** — Asymmetric-info wiring: `DispatchPackage.visibility` feeds ADR-028 Perception Rewriter + Plan 03 ProjectionFilter. Depends on B.

Each of C–G gets its own writing-plans pass when that group begins.

**In-scope for Group B:**
- Referent resolution (happy, ambiguous, absent)
- `SubsystemDispatch` framework + three reference subsystems
- `NarratorDirective` injection
- Persistent Haiku session lifecycle (start, resume, reset)
- OTEL spans on every decomposer call + every subsystem dispatch

**Out-of-scope for Group B (stubbed contract only, implemented in later groups):**
- `LethalityVerdict` — Group C
- `VisibilityTag` consumer pipeline (Perception Rewriter wiring, ProjectionFilter replacement) — Group G
- `CrossAction` cross-player dispatch — wait for multiplayer session plan landed (Group G)
- Local fine-tune swap — Group E
- Training corpus capture beyond what `events` table already does — Group D
- GM panel UI tab — Group C (when there's lethality content to visualize)

`DispatchPackage` types are defined in full (including `LethalityVerdict`, `VisibilityTag`, `CrossAction` shapes) so later groups swap implementations without changing the contract. Group B emits stub values for those fields.

---

## Preflight

- [ ] **Preflight 1: Confirm Group A has merged on server `develop`**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && git checkout develop && git pull && git log --oneline origin/develop | head -10
```

Expected: a commit matching `feat: local DM group A — dead-code demolition` (or equivalent squash-merge message from PR #26) within the top ~5 commits. Verify `action_flags`, `classified_intent`, and `preprocessor.py` are absent:

```bash
grep -rn "action_flags\|ActionFlags\|classified_intent" /Users/slabgorb/Projects/oq-1/sidequest-server/sidequest --include="*.py" | grep -v test_ || echo "CLEAN"
ls /Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/agents/preprocessor.py 2>/dev/null || echo "GONE"
```

Expected: `CLEAN` and `GONE`. If either fails, Group A has not fully landed; stop and resolve before starting B.

- [ ] **Preflight 2: Confirm `TurnPhase.IntentRouting` still exists and is unused in the dispatch flow**

```bash
grep -n "IntentRouting" /Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/game/turn.py
grep -rn "IntentRouting" /Users/slabgorb/Projects/oq-1/sidequest-server/sidequest --include="*.py" | grep -v "game/turn.py\|test_"
```

Expected: first grep shows ~5 lines in `turn.py`. Second grep is empty (or only tests). This phase is a vestigial slot we are claiming for the decomposer; if production code already uses it, stop and diagnose.

- [ ] **Preflight 3: Confirm baseline server tests pass**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && just server-test 2>&1 | tail -30
```

Expected: full suite green on `develop`. If anything is already red, investigate before adding decomposer code.

- [ ] **Preflight 4: Create server feature branch as isolated worktree**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && git worktree add .worktrees/group-b -b feat/local-dm-group-b develop
```

Expected: worktree at `/Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b` on branch `feat/local-dm-group-b` based on `develop`.

- [ ] **Preflight 5: Recreate `sidequest-content` symlink inside the worktree**

From the Group A handoff gotcha: tests walk up 4 directories to find `sidequest-content`, which from `.worktrees/group-b` resolves to the wrong place.

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b && ln -sfn ../../../sidequest-content .worktrees/sidequest-content
ls -l .worktrees/sidequest-content
```

Expected: symlink resolves to the real `sidequest-content` directory. Verify genre pack lookup:

```bash
ls .worktrees/sidequest-content/genre_packs | head -3
```

Expected: at least `caverns_and_claudes`, `elemental_harmony`, etc.

- [ ] **Preflight 6: Capture pre-change test count as a regression baseline**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b && just server-test 2>&1 | tee /tmp/group-b-baseline.txt | tail -5
grep -E "passed|failed" /tmp/group-b-baseline.txt | tail -1
```

Expected: record the baseline "N passed" count. After Group B is complete, the count should have grown by the number of tests this plan adds with zero pre-existing tests broken.

> **All subsequent tasks run from `/Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b`.** Every task's Step 1 must literally `cd` there — subagents have cwd-drift bugs (Group A gotcha #1).

---

## File Structure

**Created:**

| Path | Responsibility |
|---|---|
| `sidequest/protocol/dispatch.py` | `DispatchPackage` and nested pydantic models — the decomposer's output contract. Group C/G may add fields; Group B ships the full §5 shape with stub defaults for lethality/visibility. |
| `sidequest/agents/local_dm.py` | `LocalDM` class with `async decompose(turn_state, action) -> DispatchPackage`. Owns the Haiku persistent-session lifecycle (start, resume, reset). Pure reader; emits JSON only. |
| `sidequest/agents/subsystems/__init__.py` | Subsystem registry — maps `subsystem: str` from a `SubsystemDispatch` to a callable, plus `run_dispatch(package) -> list[SubsystemOutput]` that topologically sorts by `depends_on` and runs the bank. |
| `sidequest/agents/subsystems/reflect_absence.py` | New subsystem — consumes `Referent(resolved_to=None)` or `dispatch(subsystem="reflect_absence")` and emits a narrator directive: "do not invent a follower / describe the empty room." |
| `sidequest/agents/subsystems/distinctive_detail.py` | New subsystem — consumes ambiguous-referent dispatches and emits `NarratorDirective(kind="distinctive_detail_for_referent", payload=<specific-hint>)`. |
| `sidequest/agents/subsystems/npc_agency.py` | Wraps NPC registry + disposition reads into a subsystem contract. Ports the minimum NPC behavior signal the narrator already consumes (disposition state, recent interactions) so it becomes a first-class decomposer dispatch instead of implicit prompt state. |
| `tests/protocol/test_dispatch.py` | `DispatchPackage` serialization + validation. |
| `tests/agents/test_local_dm.py` | `LocalDM` unit tests — referent resolution (happy / ambiguous / absent), session lifecycle, degraded-timeout path, JSON-parse guardrails. |
| `tests/agents/subsystems/__init__.py` | Empty. |
| `tests/agents/subsystems/test_reflect_absence.py` | Subsystem-level tests. |
| `tests/agents/subsystems/test_distinctive_detail.py` | Subsystem-level tests. |
| `tests/agents/subsystems/test_npc_agency.py` | Subsystem-level tests — uses the existing NPC registry fixture. |
| `tests/agents/test_subsystem_registry.py` | Registry + topological-sort + dispatch-bank execution tests. |
| `tests/server/test_session_handler_decomposer.py` | Wiring test — full turn via `_execute_narration_turn` with mocked Haiku client + real narrator stub; verifies decomposer fires, directives reach the narrator prompt, OTEL spans emit. |

**Modified:**

| Path | Change |
|---|---|
| `sidequest/protocol/__init__.py` | Export `DispatchPackage` and nested types. |
| `sidequest/agents/__init__.py` | Export `LocalDM`. |
| `sidequest/agents/orchestrator.py` | (a) Accept `dispatch_package` on `TurnContext`; (b) register new `narrator_directives` `PromptSection` in `build_narrator_prompt` when directives are present. |
| `sidequest/server/session_handler.py` | `_execute_narration_turn` — call `LocalDM.decompose()` before `run_narration_turn`, attach `DispatchPackage` to `turn_context`, run subsystem bank, emit OTEL. |
| `sidequest/game/turn.py` | (No schema change, but add a note comment near `IntentRouting` pointing to `LocalDM`.) |
| `sidequest/telemetry/spans.py` | Add `SPAN_LOCAL_DM_DECOMPOSE`, `SPAN_LOCAL_DM_DISPATCH`, `SPAN_LOCAL_DM_SUBSYSTEM` constants + context-manager helpers. |

---

## Task 1: Define `DispatchPackage` types in `sidequest/protocol/dispatch.py`

**Files:**
- Create: `sidequest/protocol/dispatch.py`
- Create: `tests/protocol/test_dispatch.py`
- Modify: `sidequest/protocol/__init__.py`

**Context:** The decomposer's output is a structured JSON artifact matching spec §5. We define it as pydantic models so the Haiku-emitted JSON can be parsed and validated with one call. `LethalityVerdict` and `VisibilityTag` are defined in full but given permissive defaults because Groups C and G implement their consumers; Group B only produces stub values.

Subsystem vocabulary for Group B is a fixed enum: `reflect_absence`, `distinctive_detail_hint`, `npc_agency`. Accept `str` on the wire (the decomposer is an LLM; it will not always emit enum-clean tokens) but validate against a registered set. Unknown subsystems are logged and skipped — not fatal.

- [ ] **Step 1: `cd` into the worktree and create the tests/protocol directory if missing**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b
mkdir -p tests/protocol
touch tests/protocol/__init__.py
```

- [ ] **Step 2: Write the failing test — `DispatchPackage` round-trips through JSON**

Create `tests/protocol/test_dispatch.py`:

```python
"""Tests for DispatchPackage types (Group B, Local DM decomposer output contract)."""
from __future__ import annotations

import json

import pytest

from sidequest.protocol.dispatch import (
    CrossAction,
    DispatchPackage,
    LethalityVerdict,
    NarratorDirective,
    PlayerDispatch,
    Referent,
    SubsystemDispatch,
    VisibilityTag,
)


def test_dispatch_package_minimal_valid():
    """A package with no actions and no cross-player events is valid."""
    pkg = DispatchPackage(
        turn_id="turn-001",
        per_player=[],
        cross_player=[],
        confidence_global=1.0,
        degraded=False,
        degraded_reason=None,
    )
    assert pkg.degraded is False
    assert pkg.per_player == []


def test_dispatch_package_full_roundtrip():
    """A package containing every field type serializes and round-trips."""
    pkg = DispatchPackage(
        turn_id="turn-042",
        per_player=[
            PlayerDispatch(
                player_id="player:Alice",
                raw_action="Let's attack him!",
                resolved=[
                    Referent(
                        token="him",
                        resolved_to="npc:goblin_2",
                        confidence=0.55,
                        alternatives=["npc:goblin_1", "npc:bandit_1"],
                        resolution_note="most recent direct combatant",
                    ),
                    Referent(
                        token="let's",
                        resolved_to=None,
                        confidence=0.0,
                        alternatives=[],
                        resolution_note="no party present",
                    ),
                ],
                dispatch=[
                    SubsystemDispatch(
                        subsystem="distinctive_detail_hint",
                        params={"target": "npc:goblin_2", "hint": "broken tooth"},
                        depends_on=[],
                        idempotency_key="idem:turn-042:alice:0",
                        visibility=VisibilityTag(
                            visible_to="all",
                            perception_fidelity={},
                            secrets_for=[],
                            redact_from_narrator_canonical=False,
                        ),
                    ),
                    SubsystemDispatch(
                        subsystem="reflect_absence",
                        params={"addressee_hint": "no party"},
                        depends_on=[],
                        idempotency_key="idem:turn-042:alice:1",
                        visibility=VisibilityTag(
                            visible_to="all",
                            perception_fidelity={},
                            secrets_for=[],
                            redact_from_narrator_canonical=False,
                        ),
                    ),
                ],
                lethality=[],
                narrator_instructions=[
                    NarratorDirective(
                        kind="must_not_narrate",
                        payload="inventing an NPC follower",
                        visibility=VisibilityTag(
                            visible_to="all",
                            perception_fidelity={},
                            secrets_for=[],
                            redact_from_narrator_canonical=False,
                        ),
                    ),
                ],
            ),
        ],
        cross_player=[],
        confidence_global=0.78,
        degraded=False,
        degraded_reason=None,
    )
    serialized = pkg.model_dump_json()
    parsed = DispatchPackage.model_validate_json(serialized)
    assert parsed == pkg


def test_visibility_tag_defaults_are_explicit():
    """Visibility tags require explicit visible_to — no implicit fallback."""
    # 'all' is a conscious choice; model should accept it.
    tag = VisibilityTag(visible_to="all", perception_fidelity={}, secrets_for=[], redact_from_narrator_canonical=False)
    assert tag.visible_to == "all"
    # Player-list is also accepted.
    tag2 = VisibilityTag(visible_to=["player:Alice"], perception_fidelity={"player:Alice": "full"}, secrets_for=[], redact_from_narrator_canonical=False)
    assert tag2.visible_to == ["player:Alice"]


def test_lethality_verdict_captures_witness_scope():
    """Spec §4.2 — verdict carries witness_scope for Group G consumption."""
    verdict = LethalityVerdict(
        entity="player:Alice",
        verdict="dead",
        cause="Salt Burrower mandible crush, 34 dmg, HP -8",
        reversibility="permanent",
        narrator_directive="Alice is dead. Compose a genre-true death.",
        soul_md_constraint="genre_truth:lethal_for_this_genre",
        witness_scope={
            "direct_witnesses": ["player:Alice"],
            "indirect_witnesses": ["player:Bob"],
            "unaware": ["player:Cass"],
            "perception_fidelity": {"player:Alice": "full", "player:Bob": "audio_only_muffled"},
        },
    )
    assert verdict.witness_scope["direct_witnesses"] == ["player:Alice"]


def test_cross_action_names_participants_and_witnesses():
    """Spec §5 — cross_player entries distinguish participants from witnesses."""
    ca = CrossAction(
        participants=["player:Alice", "player:Bob"],
        witnesses=["player:Alice", "player:Bob", "player:Cass"],
        dispatch=[],
    )
    assert set(ca.witnesses) >= set(ca.participants)


def test_dispatch_package_degraded_reason_required_when_degraded():
    """Spec §6.6 — degraded=True means degraded_reason is non-null."""
    with pytest.raises(ValueError):
        DispatchPackage(
            turn_id="turn-err",
            per_player=[],
            cross_player=[],
            confidence_global=0.0,
            degraded=True,
            degraded_reason=None,
        )


def test_dispatch_package_parses_from_llm_style_json():
    """The decomposer emits raw JSON; parser must accept it."""
    raw = json.dumps({
        "turn_id": "turn-x",
        "per_player": [],
        "cross_player": [],
        "confidence_global": 0.9,
        "degraded": False,
        "degraded_reason": None,
    })
    pkg = DispatchPackage.model_validate_json(raw)
    assert pkg.turn_id == "turn-x"
```

- [ ] **Step 3: Run the test to verify it fails**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b && uv run pytest tests/protocol/test_dispatch.py -v 2>&1 | tail -20
```

Expected: `ImportError` / `ModuleNotFoundError: No module named 'sidequest.protocol.dispatch'`. If it's any other error, fix before continuing.

- [ ] **Step 4: Implement `sidequest/protocol/dispatch.py`**

```python
"""DispatchPackage — the Local DM decomposer's structured output.

Spec: docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md §5

The decomposer reads (action, state, submissions) and emits a DispatchPackage
per turn. Downstream consumers:
  - Subsystem bank — executes SubsystemDispatch entries, feeds back to state
  - Narrator prompt builder — injects NarratorDirective entries into <game_state>
  - Group G (future) — reads VisibilityTag via Perception Rewriter + ProjectionFilter

Group B emits stub values for LethalityVerdict (Group C fills in) and
VisibilityTag (Group G wires the consumer pipeline).

No tool-calling. No prose. Structured JSON only — spec §3.2.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Visibility
# ---------------------------------------------------------------------------

PerceptionFidelity = Literal[
    "full",
    "audio_only",
    "audio_only_muffled",
    "visual_only",
    "periphery_only",
    "inferred_from_aftermath",
]


class VisibilityTag(BaseModel):
    """Authoritative ground-truth visibility for a dispatch/directive/verdict.

    Consumed by ADR-028 Perception Rewriter and Plan 03 ProjectionFilter.
    Group B always emits `visible_to="all"` with empty fidelity; Group G
    fills in asymmetric values.
    """

    visible_to: list[str] | Literal["all"] = Field(description="Recipients; 'all' is a conscious choice, not a fallback.")
    perception_fidelity: dict[str, PerceptionFidelity] = Field(default_factory=dict)
    secrets_for: list[str] = Field(default_factory=list)
    redact_from_narrator_canonical: bool = False


# ---------------------------------------------------------------------------
# Referent resolution
# ---------------------------------------------------------------------------


class Referent(BaseModel):
    token: str = Field(description="The surface token from raw_action, e.g. 'him', 'let's', 'that'.")
    resolved_to: str | None = Field(description="Entity id, or None for absence.")
    confidence: float = Field(ge=0.0, le=1.0)
    alternatives: list[str] = Field(default_factory=list)
    resolution_note: str | None = None


# ---------------------------------------------------------------------------
# Subsystem dispatch
# ---------------------------------------------------------------------------


class SubsystemDispatch(BaseModel):
    subsystem: str = Field(description="Subsystem name — must be registered at runtime.")
    params: dict = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list, description="List of sibling idempotency_keys this dispatch depends on.")
    idempotency_key: str
    visibility: VisibilityTag


# ---------------------------------------------------------------------------
# Narrator directives
# ---------------------------------------------------------------------------


NarratorDirectiveKind = Literal[
    "must_narrate",
    "must_not_narrate",
    "distinctive_detail_for_referent",
    "canonical_only_do_not_reveal_to_others",
]


class NarratorDirective(BaseModel):
    kind: NarratorDirectiveKind
    payload: str
    visibility: VisibilityTag


# ---------------------------------------------------------------------------
# Lethality — full contract, stub values in Group B
# ---------------------------------------------------------------------------


LethalityVerdictKind = Literal[
    "dead",
    "dying",
    "maimed",
    "defeated",
    "captured",
    "humiliated",
    "unscathed",
]

Reversibility = Literal["permanent", "reversible_with_cost", "narrative_only"]


class LethalityVerdict(BaseModel):
    entity: str
    verdict: LethalityVerdictKind
    cause: str
    reversibility: Reversibility
    narrator_directive: str
    soul_md_constraint: str
    witness_scope: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Per-player dispatch
# ---------------------------------------------------------------------------


class PlayerDispatch(BaseModel):
    player_id: str
    raw_action: str
    resolved: list[Referent] = Field(default_factory=list)
    dispatch: list[SubsystemDispatch] = Field(default_factory=list)
    lethality: list[LethalityVerdict] = Field(default_factory=list)
    narrator_instructions: list[NarratorDirective] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Cross-player (Group G extends; Group B leaves empty)
# ---------------------------------------------------------------------------


class CrossAction(BaseModel):
    participants: list[str]
    witnesses: list[str]
    dispatch: list[SubsystemDispatch] = Field(default_factory=list)

    @model_validator(mode="after")
    def _witnesses_include_participants(self) -> "CrossAction":
        missing = set(self.participants) - set(self.witnesses)
        if missing:
            raise ValueError(f"witnesses must include all participants; missing={sorted(missing)}")
        return self


# ---------------------------------------------------------------------------
# Top-level package
# ---------------------------------------------------------------------------


class DispatchPackage(BaseModel):
    turn_id: str
    per_player: list[PlayerDispatch] = Field(default_factory=list)
    cross_player: list[CrossAction] = Field(default_factory=list)
    confidence_global: float = Field(ge=0.0, le=1.0)
    degraded: bool = False
    degraded_reason: str | None = None

    @model_validator(mode="after")
    def _degraded_requires_reason(self) -> "DispatchPackage":
        if self.degraded and not self.degraded_reason:
            raise ValueError("degraded=True requires non-null degraded_reason")
        return self

    @field_validator("per_player")
    @classmethod
    def _unique_idempotency_keys(cls, v: list[PlayerDispatch]) -> list[PlayerDispatch]:
        seen: set[str] = set()
        for pd in v:
            for d in pd.dispatch:
                if d.idempotency_key in seen:
                    raise ValueError(f"duplicate idempotency_key: {d.idempotency_key}")
                seen.add(d.idempotency_key)
        return v


__all__ = [
    "CrossAction",
    "DispatchPackage",
    "LethalityVerdict",
    "LethalityVerdictKind",
    "NarratorDirective",
    "NarratorDirectiveKind",
    "PerceptionFidelity",
    "PlayerDispatch",
    "Referent",
    "Reversibility",
    "SubsystemDispatch",
    "VisibilityTag",
]
```

- [ ] **Step 5: Re-export from `sidequest/protocol/__init__.py`**

Read the existing `__init__.py` and append (or merge into the existing export block):

```python
from sidequest.protocol.dispatch import (
    CrossAction,
    DispatchPackage,
    LethalityVerdict,
    NarratorDirective,
    PlayerDispatch,
    Referent,
    SubsystemDispatch,
    VisibilityTag,
)
```

And add each name to `__all__` if that list exists.

- [ ] **Step 6: Run the test to verify it passes**

```bash
uv run pytest tests/protocol/test_dispatch.py -v 2>&1 | tail -20
```

Expected: all 7 tests pass.

- [ ] **Step 7: Commit**

```bash
git add sidequest/protocol/dispatch.py sidequest/protocol/__init__.py tests/protocol/__init__.py tests/protocol/test_dispatch.py
git commit -m "feat(protocol): add DispatchPackage types for Local DM decomposer (group B task 1)"
```

---

## Task 2: `LocalDM` skeleton — stateless stub returning empty `DispatchPackage`

**Files:**
- Create: `sidequest/agents/local_dm.py`
- Create: `tests/agents/test_local_dm.py`
- Modify: `sidequest/agents/__init__.py`

**Context:** Build the shell before the Haiku call. A stateless `LocalDM.decompose()` that returns a valid `DispatchPackage` with no referents, no dispatches, no directives is enough to wire through the session handler (Task 10) and prove the plumbing before we pay for LLM calls. Later tasks swap the stub for the real Haiku-backed body.

- [ ] **Step 1: cd into the worktree**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b
```

- [ ] **Step 2: Write the failing test — `LocalDM.decompose()` returns an empty package**

Create `tests/agents/test_local_dm.py`:

```python
"""Tests for LocalDM — Group B decomposer MVP.

Task 2: stub returning an empty DispatchPackage.
Later tasks layer Haiku-backed resolution on top.
"""
from __future__ import annotations

import pytest

from sidequest.agents.local_dm import LocalDM
from sidequest.protocol.dispatch import DispatchPackage


@pytest.mark.asyncio
async def test_local_dm_stub_returns_empty_dispatch_package():
    """Task 2 — structural stub. Real body lands in Task 3."""
    dm = LocalDM()
    pkg = await dm.decompose(
        turn_id="turn-001",
        player_id="player:Alice",
        raw_action="I look around.",
        state_summary="You stand in a tavern.",
    )
    assert isinstance(pkg, DispatchPackage)
    assert pkg.turn_id == "turn-001"
    assert pkg.per_player == []
    assert pkg.cross_player == []
    assert pkg.degraded is False
```

- [ ] **Step 3: Run the test to verify it fails**

```bash
uv run pytest tests/agents/test_local_dm.py -v 2>&1 | tail -10
```

Expected: `ModuleNotFoundError: No module named 'sidequest.agents.local_dm'`.

- [ ] **Step 4: Create `sidequest/agents/local_dm.py` with the stub**

```python
"""LocalDM — structured-output decomposer between sealed-letter and narrator.

Spec: docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md §3-§7

Reads player action + game state. Emits DispatchPackage (spec §5).
Never writes prose. Runs on a persistent Haiku session (ADR-066 pattern).

Group B scope: single-player decompose (per spec §10 Group B).
Multiplayer batched decompose lands alongside Group G (multiplayer session
model spec — `cross_player` dispatch entries).
"""
from __future__ import annotations

from sidequest.protocol.dispatch import DispatchPackage


class LocalDM:
    """Local DM decomposer. Haiku-backed in Group B; local fine-tune in Group E."""

    def __init__(self) -> None:
        # Task 3 extends: client injection, session id, soul_data reference.
        pass

    async def decompose(
        self,
        *,
        turn_id: str,
        player_id: str,
        raw_action: str,
        state_summary: str,
    ) -> DispatchPackage:
        """Decompose one player action into a DispatchPackage.

        Group B Task 2 stub: returns an empty package so session-handler wiring
        (Task 10) can exercise the flow before the LLM call is implemented.
        Task 3 replaces this body with the Haiku call + structured-output parse.
        """
        return DispatchPackage(
            turn_id=turn_id,
            per_player=[],
            cross_player=[],
            confidence_global=1.0,
            degraded=False,
            degraded_reason=None,
        )


__all__ = ["LocalDM"]
```

- [ ] **Step 5: Re-export from `sidequest/agents/__init__.py`**

Append to the `__init__.py` (or merge into existing imports block):

```python
from sidequest.agents.local_dm import LocalDM
```

Add `"LocalDM"` to `__all__` if that list is present.

- [ ] **Step 6: Run the test to verify it passes**

```bash
uv run pytest tests/agents/test_local_dm.py -v 2>&1 | tail -10
```

Expected: 1 passed.

- [ ] **Step 7: Commit**

```bash
git add sidequest/agents/local_dm.py sidequest/agents/__init__.py tests/agents/test_local_dm.py
git commit -m "feat(agents): LocalDM skeleton returning empty DispatchPackage (group B task 2)"
```

---

## Task 3: Haiku-backed `LocalDM.decompose()` with structured-output parsing

**Files:**
- Modify: `sidequest/agents/local_dm.py`
- Modify: `tests/agents/test_local_dm.py`

**Context:** Replace the stub. The decomposer builds a prompt from the action + state, sends it to Haiku via `ClaudeClient.send_with_session` (same client path the narrator uses — ADR-066), parses the JSON response into a `DispatchPackage`, and on any parse / timeout failure returns a `degraded=True` package (spec §6.6).

The prompt is small and structure-focused. It must:
1. State the decomposer's role: "impartial server-side reader, structured JSON only."
2. Describe the `DispatchPackage` schema (pydantic JSON schema embedded).
3. Provide the game state.
4. Provide the raw action.
5. Ask for a `DispatchPackage`.

Three known subsystem names (`reflect_absence`, `distinctive_detail_hint`, `npc_agency`) are advertised in the prompt. Unknown subsystem names in the response are logged and skipped by the dispatcher (Task 7) — not an error here.

The LLM interaction is mocked in tests via the existing `ClaudeLike` protocol so we don't burn tokens during development.

- [ ] **Step 1: cd to worktree**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b
```

- [ ] **Step 2: Extend `tests/agents/test_local_dm.py` with LLM-backed tests**

Append to the file:

```python
import json
from unittest.mock import AsyncMock

from sidequest.agents.claude_client import ClaudeResponse


@pytest.fixture
def dispatch_json_pronoun_resolved():
    """Haiku returns a DispatchPackage resolving 'him' to goblin_2."""
    return json.dumps({
        "turn_id": "turn-010",
        "per_player": [{
            "player_id": "player:Alice",
            "raw_action": "Attack him!",
            "resolved": [{
                "token": "him",
                "resolved_to": "npc:goblin_2",
                "confidence": 0.55,
                "alternatives": ["npc:goblin_1", "npc:bandit_1"],
                "resolution_note": "most recent direct combatant",
            }],
            "dispatch": [{
                "subsystem": "distinctive_detail_hint",
                "params": {"target": "npc:goblin_2", "hint": "broken tooth"},
                "depends_on": [],
                "idempotency_key": "idem:turn-010:alice:0",
                "visibility": {
                    "visible_to": "all",
                    "perception_fidelity": {},
                    "secrets_for": [],
                    "redact_from_narrator_canonical": False,
                },
            }],
            "lethality": [],
            "narrator_instructions": [{
                "kind": "distinctive_detail_for_referent",
                "payload": "describe the goblin by its broken tooth",
                "visibility": {
                    "visible_to": "all",
                    "perception_fidelity": {},
                    "secrets_for": [],
                    "redact_from_narrator_canonical": False,
                },
            }],
        }],
        "cross_player": [],
        "confidence_global": 0.55,
        "degraded": False,
        "degraded_reason": None,
    })


@pytest.fixture
def dispatch_json_absence():
    """Haiku returns a DispatchPackage resolving 'let's' to absence."""
    return json.dumps({
        "turn_id": "turn-011",
        "per_player": [{
            "player_id": "player:Alice",
            "raw_action": "Let's go!",
            "resolved": [{
                "token": "let's",
                "resolved_to": None,
                "confidence": 0.0,
                "alternatives": [],
                "resolution_note": "no party present in scene",
            }],
            "dispatch": [{
                "subsystem": "reflect_absence",
                "params": {"addressee_hint": "no party"},
                "depends_on": [],
                "idempotency_key": "idem:turn-011:alice:0",
                "visibility": {
                    "visible_to": "all",
                    "perception_fidelity": {},
                    "secrets_for": [],
                    "redact_from_narrator_canonical": False,
                },
            }],
            "lethality": [],
            "narrator_instructions": [{
                "kind": "must_not_narrate",
                "payload": "inventing an NPC follower",
                "visibility": {
                    "visible_to": "all",
                    "perception_fidelity": {},
                    "secrets_for": [],
                    "redact_from_narrator_canonical": False,
                },
            }, {
                "kind": "must_narrate",
                "payload": "the empty room answering back",
                "visibility": {
                    "visible_to": "all",
                    "perception_fidelity": {},
                    "secrets_for": [],
                    "redact_from_narrator_canonical": False,
                },
            }],
        }],
        "cross_player": [],
        "confidence_global": 1.0,
        "degraded": False,
        "degraded_reason": None,
    })


def _make_mock_client(response_text: str) -> AsyncMock:
    """Build a mocked ClaudeLike client returning the given structured response."""
    client = AsyncMock()
    client.send_with_session = AsyncMock(return_value=ClaudeResponse(
        text=response_text,
        session_id="decomposer-session-abc",
        stop_reason="end_turn",
    ))
    return client


@pytest.mark.asyncio
async def test_local_dm_resolves_pronoun_via_haiku(dispatch_json_pronoun_resolved):
    client = _make_mock_client(dispatch_json_pronoun_resolved)
    dm = LocalDM(client=client)

    pkg = await dm.decompose(
        turn_id="turn-010",
        player_id="player:Alice",
        raw_action="Attack him!",
        state_summary="Goblins 1-3 and a bandit are in the room.",
    )

    assert pkg.degraded is False
    assert len(pkg.per_player) == 1
    dispatch = pkg.per_player[0]
    assert dispatch.resolved[0].resolved_to == "npc:goblin_2"
    assert "npc:goblin_1" in dispatch.resolved[0].alternatives
    # At least one call was made.
    assert client.send_with_session.await_count == 1


@pytest.mark.asyncio
async def test_local_dm_handles_absence(dispatch_json_absence):
    client = _make_mock_client(dispatch_json_absence)
    dm = LocalDM(client=client)

    pkg = await dm.decompose(
        turn_id="turn-011",
        player_id="player:Alice",
        raw_action="Let's go!",
        state_summary="You are alone in the tavern.",
    )

    assert pkg.per_player[0].resolved[0].resolved_to is None
    # Directives include both must_not and must — the absence response shape.
    kinds = [d.kind for d in pkg.per_player[0].narrator_instructions]
    assert "must_not_narrate" in kinds
    assert "must_narrate" in kinds


@pytest.mark.asyncio
async def test_local_dm_degraded_on_parse_failure():
    """If Haiku returns unparsable JSON, decomposer returns degraded package (spec §6.6)."""
    client = _make_mock_client("not json at all")
    dm = LocalDM(client=client)

    pkg = await dm.decompose(
        turn_id="turn-err",
        player_id="player:Alice",
        raw_action="anything",
        state_summary="...",
    )
    assert pkg.degraded is True
    assert pkg.degraded_reason
    assert pkg.turn_id == "turn-err"
    assert pkg.per_player == []


@pytest.mark.asyncio
async def test_local_dm_degraded_on_client_exception():
    """Client timeout / network error → degraded package, no crash."""
    client = AsyncMock()
    client.send_with_session = AsyncMock(side_effect=TimeoutError("decomposer timeout"))
    dm = LocalDM(client=client)

    pkg = await dm.decompose(
        turn_id="turn-timeout",
        player_id="player:Alice",
        raw_action="whatever",
        state_summary="...",
    )
    assert pkg.degraded is True
    assert "timeout" in pkg.degraded_reason.lower()


@pytest.mark.asyncio
async def test_local_dm_persistent_session_resumes_on_second_call(dispatch_json_absence):
    """ADR-066 — first call establishes session; second call resumes."""
    client = _make_mock_client(dispatch_json_absence)
    dm = LocalDM(client=client)

    await dm.decompose(
        turn_id="turn-100", player_id="player:Alice",
        raw_action="x", state_summary="y",
    )
    await dm.decompose(
        turn_id="turn-101", player_id="player:Alice",
        raw_action="x", state_summary="y",
    )

    first_call_kwargs = client.send_with_session.await_args_list[0].kwargs
    second_call_kwargs = client.send_with_session.await_args_list[1].kwargs
    assert first_call_kwargs["session_id"] is None
    assert second_call_kwargs["session_id"] == "decomposer-session-abc"


@pytest.mark.asyncio
async def test_local_dm_reset_session_clears_id(dispatch_json_absence):
    """Reset returns subsequent calls to first-turn (session_id=None)."""
    client = _make_mock_client(dispatch_json_absence)
    dm = LocalDM(client=client)

    await dm.decompose(turn_id="t1", player_id="p", raw_action="x", state_summary="y")
    dm.reset_session()
    await dm.decompose(turn_id="t2", player_id="p", raw_action="x", state_summary="y")

    assert client.send_with_session.await_args_list[1].kwargs["session_id"] is None
```

- [ ] **Step 3: Run — watch the stub pass old tests, new tests fail**

```bash
uv run pytest tests/agents/test_local_dm.py -v 2>&1 | tail -25
```

Expected: Task 2 stub test still passes; Task 3 tests fail (the stub doesn't accept `client=`, doesn't call it, doesn't parse JSON).

- [ ] **Step 4: Replace `sidequest/agents/local_dm.py` with the real implementation**

```python
"""LocalDM — structured-output decomposer between sealed-letter and narrator.

Spec: docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md §3-§7

Reads player action + game state. Emits DispatchPackage (spec §5).
Never writes prose. Runs on a persistent Haiku session (ADR-066 pattern).

Group B scope: single-player decompose. Multiplayer batching lands in
Group G alongside the multiplayer session model wiring.

On any parse failure, LLM timeout, or unexpected exception, emits a
degraded=True package (spec §6.6) — the table never blocks.
"""
from __future__ import annotations

import json
import logging
from threading import Lock

from pydantic import ValidationError

from sidequest.agents.claude_client import ClaudeClient, ClaudeLike
from sidequest.protocol.dispatch import DispatchPackage

logger = logging.getLogger(__name__)

DECOMPOSER_MODEL = "haiku"

# Advertised subsystem vocabulary for Phase A. New subsystems are added to
# this list as they land (Groups C-G). The subsystem registry (Task 7)
# is the runtime authority; this is documentation for the prompt.
KNOWN_SUBSYSTEMS: tuple[str, ...] = (
    "reflect_absence",
    "distinctive_detail_hint",
    "npc_agency",
)


_DECOMPOSER_SYSTEM_PROMPT = """You are the Local DM — an impartial structured-output reader.

Your job: read a player's action + the game state, then emit ONE JSON object
matching the DispatchPackage schema. Never write prose. Never call tools.
Output JSON only — no preamble, no explanation, no markdown fences.

You are fair to NPC agendas, fair to genre lethality, fair to physics,
fair to the player — in that order when they conflict. You do not soften
outcomes to spare the player. You do not invent hostile outcomes the state
doesn't warrant. Impartiality cuts both ways.

For each player action:
  1. Resolve referents (pronouns, ellipses, demonstratives). Every resolution
     carries a confidence 0.0-1.0 and plausible alternatives. If nothing
     plausibly resolves, set resolved_to=null with confidence=0 — do NOT
     invent a filler.
  2. Emit subsystem dispatches. Known subsystems:
       - reflect_absence — use when an addressee is unresolved; do not invent
         followers.
       - distinctive_detail_hint — use when a referent is ambiguous; provide
         a distinctive detail (e.g., "broken tooth") so the narrator names
         the target cleanly.
       - npc_agency — use when an NPC needs to decide or react.
  3. Emit narrator_instructions — must_narrate / must_not_narrate /
     distinctive_detail_for_referent / canonical_only_do_not_reveal_to_others.
  4. Set confidence_global to your overall confidence across the turn.

Every dispatch carries a visibility tag. For Phase A, emit
visible_to="all" with empty perception_fidelity unless the state clearly
names asymmetric visibility.

OUTPUT: exactly one JSON object, DispatchPackage shape. No other text."""


def _build_user_prompt(turn_id: str, player_id: str, raw_action: str, state_summary: str) -> str:
    return (
        f"turn_id: {turn_id}\n"
        f"player_id: {player_id}\n"
        f"<game_state>\n{state_summary}\n</game_state>\n"
        f"<raw_action>\n{raw_action}\n</raw_action>\n"
        f"Emit DispatchPackage JSON for this single action."
    )


class LocalDM:
    """Local DM decomposer.

    Haiku-backed in Group B; swap for local fine-tune in Group E by
    replacing the `ClaudeLike` client injection.
    """

    def __init__(self, client: ClaudeLike | None = None) -> None:
        self._client: ClaudeLike = client if client is not None else ClaudeClient()
        self._session_id: str | None = None
        self._session_lock: Lock = Lock()

    def reset_session(self) -> None:
        """Clear the persistent session id (ADR-066 reset semantics)."""
        with self._session_lock:
            self._session_id = None

    async def decompose(
        self,
        *,
        turn_id: str,
        player_id: str,
        raw_action: str,
        state_summary: str,
    ) -> DispatchPackage:
        """Decompose one player action into a DispatchPackage.

        On any failure returns a degraded=True package per spec §6.6 —
        the table never blocks.
        """
        user_prompt = _build_user_prompt(turn_id, player_id, raw_action, state_summary)

        with self._session_lock:
            current_session = self._session_id

        try:
            response = await self._client.send_with_session(
                prompt=user_prompt,
                model=DECOMPOSER_MODEL,
                session_id=current_session,
                system_prompt=_DECOMPOSER_SYSTEM_PROMPT if current_session is None else None,
                allowed_tools=[],
                env_vars={},
            )
        except Exception as exc:  # TimeoutError, subprocess failure, whatever.
            logger.warning("local_dm.client_exception turn_id=%s exc=%s", turn_id, exc)
            return _degraded_package(turn_id, reason=f"client_exception: {exc}")

        # Cache session id after first successful call.
        if response.session_id:
            with self._session_lock:
                self._session_id = response.session_id

        raw_text = (response.text or "").strip()
        if not raw_text:
            logger.warning("local_dm.empty_response turn_id=%s", turn_id)
            return _degraded_package(turn_id, reason="empty_response")

        try:
            pkg = DispatchPackage.model_validate_json(raw_text)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("local_dm.parse_failure turn_id=%s exc=%s", turn_id, exc)
            return _degraded_package(turn_id, reason=f"parse_failure: {type(exc).__name__}")

        return pkg


def _degraded_package(turn_id: str, *, reason: str) -> DispatchPackage:
    return DispatchPackage(
        turn_id=turn_id,
        per_player=[],
        cross_player=[],
        confidence_global=0.0,
        degraded=True,
        degraded_reason=reason,
    )


__all__ = ["DECOMPOSER_MODEL", "KNOWN_SUBSYSTEMS", "LocalDM"]
```

- [ ] **Step 5: Run the tests**

```bash
uv run pytest tests/agents/test_local_dm.py -v 2>&1 | tail -30
```

Expected: all 8 tests pass (the 1 stub test from Task 2 + 7 new).

- [ ] **Step 6: Commit**

```bash
git add sidequest/agents/local_dm.py tests/agents/test_local_dm.py
git commit -m "feat(agents): Haiku-backed LocalDM.decompose with structured output (group B task 3)"
```

---

## Task 4: Subsystem — `reflect_absence`

**Files:**
- Create: `sidequest/agents/subsystems/__init__.py`
- Create: `sidequest/agents/subsystems/reflect_absence.py`
- Create: `tests/agents/subsystems/__init__.py`
- Create: `tests/agents/subsystems/test_reflect_absence.py`

**Context:** The first subsystem. It is **pure narrative-directive generation** — it consumes a `SubsystemDispatch(subsystem="reflect_absence", ...)` and emits one or more `NarratorDirective` entries plus nothing else. Per spec §6.3, when a player addresses no one present, the subsystem tells the narrator to describe the empty room answering back rather than invent a follower.

We intentionally keep subsystems as plain async callables with a typed input/output contract. No class hierarchy. A registry (Task 7) maps subsystem-name → callable.

- [ ] **Step 1: cd to worktree + create package dirs**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b
mkdir -p sidequest/agents/subsystems tests/agents/subsystems
touch sidequest/agents/subsystems/__init__.py tests/agents/subsystems/__init__.py
```

- [ ] **Step 2: Write the failing test — `reflect_absence` emits a `must_not_narrate("invent follower") + must_narrate("empty room")` pair**

Create `tests/agents/subsystems/test_reflect_absence.py`:

```python
"""Tests for the reflect_absence subsystem.

Spec: decomposer-design.md §6.3 — unresolvable referent path.
"""
from __future__ import annotations

import pytest

from sidequest.agents.subsystems.reflect_absence import run_reflect_absence
from sidequest.protocol.dispatch import SubsystemDispatch, VisibilityTag


def _tag_all() -> VisibilityTag:
    return VisibilityTag(
        visible_to="all",
        perception_fidelity={},
        secrets_for=[],
        redact_from_narrator_canonical=False,
    )


@pytest.mark.asyncio
async def test_reflect_absence_emits_must_not_and_must_directives():
    dispatch = SubsystemDispatch(
        subsystem="reflect_absence",
        params={"addressee_hint": "no party"},
        depends_on=[],
        idempotency_key="idem:t:p:0",
        visibility=_tag_all(),
    )
    directives = await run_reflect_absence(dispatch)
    kinds = {d.kind for d in directives}
    assert "must_not_narrate" in kinds
    assert "must_narrate" in kinds
    # Must-not payload references invention.
    must_nots = [d for d in directives if d.kind == "must_not_narrate"]
    assert any("invent" in d.payload.lower() or "follower" in d.payload.lower() for d in must_nots)
    # Must-narrate payload references emptiness.
    musts = [d for d in directives if d.kind == "must_narrate"]
    assert any("empty" in d.payload.lower() or "absence" in d.payload.lower() for d in musts)


@pytest.mark.asyncio
async def test_reflect_absence_propagates_visibility_tag():
    """Directives inherit the dispatch's visibility tag by default."""
    tag = VisibilityTag(
        visible_to=["player:Alice"],
        perception_fidelity={"player:Alice": "full"},
        secrets_for=[],
        redact_from_narrator_canonical=False,
    )
    dispatch = SubsystemDispatch(
        subsystem="reflect_absence",
        params={},
        depends_on=[],
        idempotency_key="idem:x",
        visibility=tag,
    )
    directives = await run_reflect_absence(dispatch)
    assert all(d.visibility == tag for d in directives)
```

- [ ] **Step 3: Run the test to verify it fails**

```bash
uv run pytest tests/agents/subsystems/test_reflect_absence.py -v 2>&1 | tail -10
```

Expected: `ModuleNotFoundError: No module named 'sidequest.agents.subsystems.reflect_absence'`.

- [ ] **Step 4: Implement `sidequest/agents/subsystems/reflect_absence.py`**

```python
"""reflect_absence subsystem — spec §6.3.

When a player addresses no one present, the narrator must describe the
absence honestly rather than invent a follower. This subsystem emits the
directive pair that enforces that.
"""
from __future__ import annotations

from sidequest.protocol.dispatch import NarratorDirective, SubsystemDispatch


async def run_reflect_absence(dispatch: SubsystemDispatch) -> list[NarratorDirective]:
    """Return directives forcing honest-absence narration."""
    tag = dispatch.visibility
    return [
        NarratorDirective(
            kind="must_not_narrate",
            payload="inventing an NPC follower or off-screen responder",
            visibility=tag,
        ),
        NarratorDirective(
            kind="must_narrate",
            payload="the empty room answering back — the absence itself is the scene",
            visibility=tag,
        ),
    ]


__all__ = ["run_reflect_absence"]
```

- [ ] **Step 5: Run — verify pass**

```bash
uv run pytest tests/agents/subsystems/test_reflect_absence.py -v 2>&1 | tail -10
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add sidequest/agents/subsystems/__init__.py sidequest/agents/subsystems/reflect_absence.py tests/agents/subsystems/__init__.py tests/agents/subsystems/test_reflect_absence.py
git commit -m "feat(subsystems): reflect_absence — honest absence directives (group B task 4)"
```

---

## Task 5: Subsystem — `distinctive_detail_hint`

**Files:**
- Create: `sidequest/agents/subsystems/distinctive_detail.py`
- Create: `tests/agents/subsystems/test_distinctive_detail.py`

**Context:** Spec §6.2 — when a pronoun is ambiguous (`"him"` could mean any of three hostiles), the decomposer picks the most-plausible target with surfaced confidence + alternatives, and this subsystem emits a `NarratorDirective(kind="distinctive_detail_for_referent")` with a specific hint (e.g., `"broken tooth"`). The narrator then writes prose that *names* the target distinctively, giving the player a clean retarget opportunity on the next turn (handled in §6.2 by next-turn retarget logic, out of scope for Group B).

`params` carries `target` (entity id) and `hint` (short human-readable distinctive feature). The subsystem validates both are present and produces exactly one directive.

- [ ] **Step 1: cd to worktree**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b
```

- [ ] **Step 2: Write the failing test**

Create `tests/agents/subsystems/test_distinctive_detail.py`:

```python
"""Tests for distinctive_detail_hint subsystem (spec §6.2)."""
from __future__ import annotations

import pytest

from sidequest.agents.subsystems.distinctive_detail import run_distinctive_detail
from sidequest.protocol.dispatch import SubsystemDispatch, VisibilityTag


def _tag_all() -> VisibilityTag:
    return VisibilityTag(
        visible_to="all", perception_fidelity={}, secrets_for=[],
        redact_from_narrator_canonical=False,
    )


@pytest.mark.asyncio
async def test_distinctive_detail_emits_single_narrator_directive():
    dispatch = SubsystemDispatch(
        subsystem="distinctive_detail_hint",
        params={"target": "npc:goblin_2", "hint": "broken tooth"},
        depends_on=[],
        idempotency_key="idem:a",
        visibility=_tag_all(),
    )
    directives = await run_distinctive_detail(dispatch)
    assert len(directives) == 1
    d = directives[0]
    assert d.kind == "distinctive_detail_for_referent"
    assert "npc:goblin_2" in d.payload
    assert "broken tooth" in d.payload


@pytest.mark.asyncio
async def test_distinctive_detail_raises_on_missing_target():
    dispatch = SubsystemDispatch(
        subsystem="distinctive_detail_hint",
        params={"hint": "broken tooth"},  # missing target
        depends_on=[],
        idempotency_key="idem:b",
        visibility=_tag_all(),
    )
    with pytest.raises(ValueError, match="target"):
        await run_distinctive_detail(dispatch)


@pytest.mark.asyncio
async def test_distinctive_detail_raises_on_missing_hint():
    dispatch = SubsystemDispatch(
        subsystem="distinctive_detail_hint",
        params={"target": "npc:goblin_2"},  # missing hint
        depends_on=[],
        idempotency_key="idem:c",
        visibility=_tag_all(),
    )
    with pytest.raises(ValueError, match="hint"):
        await run_distinctive_detail(dispatch)
```

- [ ] **Step 3: Run — verify fail**

```bash
uv run pytest tests/agents/subsystems/test_distinctive_detail.py -v 2>&1 | tail -10
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 4: Implement `sidequest/agents/subsystems/distinctive_detail.py`**

```python
"""distinctive_detail_hint subsystem — spec §6.2.

When a referent is ambiguous, emit a narrator directive naming the chosen
target with a distinctive detail so the prose identifies it cleanly.
"""
from __future__ import annotations

from sidequest.protocol.dispatch import NarratorDirective, SubsystemDispatch


async def run_distinctive_detail(dispatch: SubsystemDispatch) -> list[NarratorDirective]:
    target = dispatch.params.get("target")
    hint = dispatch.params.get("hint")
    if not target:
        raise ValueError("distinctive_detail_hint requires params.target")
    if not hint:
        raise ValueError("distinctive_detail_hint requires params.hint")

    return [
        NarratorDirective(
            kind="distinctive_detail_for_referent",
            payload=f"name {target} by its distinctive detail: {hint}",
            visibility=dispatch.visibility,
        ),
    ]


__all__ = ["run_distinctive_detail"]
```

- [ ] **Step 5: Run — verify pass**

```bash
uv run pytest tests/agents/subsystems/test_distinctive_detail.py -v 2>&1 | tail -10
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add sidequest/agents/subsystems/distinctive_detail.py tests/agents/subsystems/test_distinctive_detail.py
git commit -m "feat(subsystems): distinctive_detail_hint directive emission (group B task 5)"
```

---

## Task 6: Subsystem — `npc_agency` wrapper

**Files:**
- Create: `sidequest/agents/subsystems/npc_agency.py`
- Create: `tests/agents/subsystems/test_npc_agency.py`

**Context:** This is the only subsystem in Group B that reads **existing** state rather than purely generating directives. In the Python port the NPC registry is `snapshot.npc_registry: list[NpcRegistryEntry]` (`sidequest/game/session.py:373`). `NpcRegistryEntry` (line 129) carries `name`, `role`, `pronouns`, `appearance`, `last_seen_location`, `last_seen_turn` — **no disposition field**. Disposition-by-npc lives in tension/affinity trackers and confrontation pools, neither fully wired through a single lookup yet.

**Scope in Group B:** `npc_agency` surfaces the fields that *are* available — the registry entry's name, role, and last-seen context — as structured data plus a narrator directive noting the NPC's last-known presence. Disposition-aware behavior is explicitly a Group C extension when the confrontation / tension-tracker plumbing lands.

Given a `SubsystemDispatch(subsystem="npc_agency", params={"npc_name": ..., "situation": ...})`, the subsystem:
- Looks the name up in the registry entries (linear search — the list is small)
- Returns a `SubsystemOutput` carrying (a) a narrator directive `must_narrate` with role + last-seen framing, (b) `data` with the fields Group C / Group G will consume.

The subsystem takes the dispatch plus the registry list as kwargs. The Task 7 registry wires the snapshot's registry through.

**Subsystem output type:** a new `SubsystemOutput` dataclass in `subsystems/__init__.py` that carries emitted directives + arbitrary structured data for downstream consumers. This lets non-directive-only subsystems return state that the lethality arbiter (Group C) and state-patch layer (AgentExecution phase) can pick up.

- [ ] **Step 1: cd to worktree + discover existing NPC fixtures**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b
grep -rln "NpcRegistryEntry\|npc_registry=" tests/ --include="*.py" | head -5
```

Note which test file already builds `NpcRegistryEntry` instances; reuse its construction pattern in Step 2. The real class (`sidequest/game/session.py:129`) has fields `name`, `role`, `pronouns`, `appearance`, `last_seen_location`, `last_seen_turn`.

- [ ] **Step 2: Define the shared `SubsystemOutput` dataclass in `subsystems/__init__.py`**

Edit `sidequest/agents/subsystems/__init__.py`:

```python
"""Subsystem package — Local DM dispatch consumers.

Each subsystem is an async callable that takes a SubsystemDispatch (and
optionally additional state) and returns a SubsystemOutput. The Task 7
registry maps subsystem names to callables and runs the dispatch bank.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sidequest.protocol.dispatch import NarratorDirective


@dataclass
class SubsystemOutput:
    """Output of one subsystem dispatch.

    Directives feed the narrator prompt. Data feeds downstream subsystems
    (e.g., Group C lethality reads npc_agency disposition from here) and
    the StatePatch phase.
    """

    directives: list[NarratorDirective] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


__all__ = ["SubsystemOutput"]
```

- [ ] **Step 3: Write the failing test — NPC agency looks up NPC state and emits a disposition-appropriate directive**

Create `tests/agents/subsystems/test_npc_agency.py`:

```python
"""Tests for npc_agency subsystem (wraps existing NPC registry)."""
from __future__ import annotations

import pytest

from sidequest.agents.subsystems import SubsystemOutput
from sidequest.agents.subsystems.npc_agency import run_npc_agency
from sidequest.protocol.dispatch import SubsystemDispatch, VisibilityTag


def _tag_all() -> VisibilityTag:
    return VisibilityTag(
        visible_to="all", perception_fidelity={}, secrets_for=[],
        redact_from_narrator_canonical=False,
    )


@pytest.mark.asyncio
async def test_npc_agency_returns_output_with_directive_and_data(minimal_npc_registry):
    """Looking up a known NPC emits a must_narrate directive + structured data."""
    dispatch = SubsystemDispatch(
        subsystem="npc_agency",
        params={"npc_name": "Harlan", "situation": "player enters the inn"},
        depends_on=[],
        idempotency_key="idem:a",
        visibility=_tag_all(),
    )
    out = await run_npc_agency(dispatch, npc_registry=minimal_npc_registry)
    assert isinstance(out, SubsystemOutput)
    assert out.data["npc_name"] == "Harlan"
    assert out.data["role"] == "innkeeper"
    assert out.data["last_seen_location"] == "the inn"
    assert len(out.directives) == 1
    d = out.directives[0]
    assert d.kind == "must_narrate"
    assert "Harlan" in d.payload
    assert "innkeeper" in d.payload.lower() or "inn" in d.payload.lower()


@pytest.mark.asyncio
async def test_npc_agency_unknown_npc_returns_no_directive_with_error_data(minimal_npc_registry):
    """Unknown NPC name yields empty directives + diagnostic data, not an exception."""
    dispatch = SubsystemDispatch(
        subsystem="npc_agency",
        params={"npc_name": "NotAnNpc", "situation": "x"},
        depends_on=[],
        idempotency_key="idem:b",
        visibility=_tag_all(),
    )
    out = await run_npc_agency(dispatch, npc_registry=minimal_npc_registry)
    assert out.directives == []
    assert out.data.get("error") == "npc_not_registered"
    assert out.data.get("npc_name") == "NotAnNpc"


@pytest.mark.asyncio
async def test_npc_agency_raises_on_missing_npc_name(minimal_npc_registry):
    dispatch = SubsystemDispatch(
        subsystem="npc_agency",
        params={"situation": "x"},
        depends_on=[],
        idempotency_key="idem:c",
        visibility=_tag_all(),
    )
    with pytest.raises(ValueError, match="npc_name"):
        await run_npc_agency(dispatch, npc_registry=minimal_npc_registry)
```

Create `tests/agents/subsystems/conftest.py`:

```python
"""Fixtures for subsystem tests."""
from __future__ import annotations

import pytest

from sidequest.game.session import NpcRegistryEntry


@pytest.fixture
def minimal_npc_registry() -> list[NpcRegistryEntry]:
    """A small registry list with one named NPC.

    The Python port stores the NPC registry as ``list[NpcRegistryEntry]`` on
    ``WorldSnapshot.npc_registry`` (see ``sidequest/game/session.py``).
    """
    return [
        NpcRegistryEntry(
            name="Harlan",
            role="innkeeper",
            pronouns="he/him",
            appearance="grey beard, apron",
            last_seen_location="the inn",
            last_seen_turn=1,
        ),
    ]
```

> **NPC lookup is by `name`, not by any synthetic id.** The Python port's registry is a plain list of pydantic entries; `npc_agency` does a linear search (fine — lists are small, ~5-20 entries per scene).

- [ ] **Step 4: Run — verify fail**

```bash
uv run pytest tests/agents/subsystems/test_npc_agency.py -v 2>&1 | tail -15
```

Expected: `ModuleNotFoundError` on `sidequest.agents.subsystems.npc_agency`.

- [ ] **Step 5: Implement `sidequest/agents/subsystems/npc_agency.py`**

```python
"""npc_agency subsystem — surfaces registry facts for decomposer dispatch.

Group B scope: look up an NPC by name in the snapshot's NpcRegistryEntry
list, emit a must_narrate directive framing role + last-seen context, and
surface the same fields as structured data for downstream consumers.

Group C extends this to consume confrontation resource pools + tension
tracker state and emit disposition-aware directives / lethality-arbiter
input. NpcRegistryEntry in the Python port today has no disposition field.
"""
from __future__ import annotations

from sidequest.agents.subsystems import SubsystemOutput
from sidequest.game.session import NpcRegistryEntry
from sidequest.protocol.dispatch import NarratorDirective, SubsystemDispatch


async def run_npc_agency(
    dispatch: SubsystemDispatch,
    *,
    npc_registry: list[NpcRegistryEntry],
) -> SubsystemOutput:
    """Surface NpcRegistryEntry facts as a narrator directive + structured data."""
    npc_name = dispatch.params.get("npc_name")
    situation = dispatch.params.get("situation", "unspecified")
    if not npc_name:
        raise ValueError("npc_agency requires params.npc_name")

    entry = next((e for e in npc_registry if e.name == npc_name), None)
    if entry is None:
        return SubsystemOutput(
            directives=[],
            data={"error": "npc_not_registered", "npc_name": npc_name},
        )

    role_frag = f"({entry.role})" if entry.role else ""
    location_frag = f"last seen at {entry.last_seen_location}" if entry.last_seen_location else ""
    directive = NarratorDirective(
        kind="must_narrate",
        payload=(
            f"{entry.name} {role_frag} responds to {situation} consistent with "
            f"their established role; {location_frag}. Do not invent a new "
            f"identity or relocate them silently."
        ).strip(),
        visibility=dispatch.visibility,
    )
    return SubsystemOutput(
        directives=[directive],
        data={
            "npc_name": entry.name,
            "role": entry.role,
            "last_seen_location": entry.last_seen_location,
            "last_seen_turn": entry.last_seen_turn,
            "situation": situation,
        },
    )


__all__ = ["run_npc_agency"]
```

- [ ] **Step 6: Run the tests**

```bash
uv run pytest tests/agents/subsystems/ -v 2>&1 | tail -25
```

Expected: all npc_agency + earlier subsystem tests pass. If NpcRegistry API differs, adjust the fixture.

- [ ] **Step 7: Commit**

```bash
git add sidequest/agents/subsystems/__init__.py sidequest/agents/subsystems/npc_agency.py tests/agents/subsystems/conftest.py tests/agents/subsystems/test_npc_agency.py
git commit -m "feat(subsystems): npc_agency wraps NPC registry lookup (group B task 6)"
```

---

## Task 7: Subsystem registry + dispatch-bank executor

**Files:**
- Modify: `sidequest/agents/subsystems/__init__.py`
- Create: `tests/agents/test_subsystem_registry.py`

**Context:** A registry maps subsystem-name → callable. The bank executor takes a full `DispatchPackage`, topologically sorts dispatches by `depends_on`, runs them (in parallel when independent, serialized when a `depends_on` edge exists), and returns the aggregated directives plus a per-idempotency-key map of subsystem outputs.

Rules (spec §8 coordination correctness):
1. **Idempotency.** If an `idempotency_key` appears twice across runs (e.g., retry), the executor runs it once and reuses the prior result (in-process cache, scope: one `DispatchPackage`).
2. **Unknown subsystems** are logged and skipped — not fatal. `KNOWN_SUBSYSTEMS` from `local_dm.py` is the advertised list but not the runtime authority; the registry is.
3. **Subsystem exceptions** are caught and logged per spec §8 "partial subsystem failures"; they do not abort the bank.
4. **`depends_on` cycles** raise `ValueError` — bug in the decomposer output, not a runtime condition.
5. **NPC registry + other shared state** is passed to every subsystem as keyword args from a single `context: SubsystemContext` object so new subsystems don't change the registry signature.

- [ ] **Step 1: Extend `sidequest/agents/subsystems/__init__.py`**

Rewrite to include registry + executor:

```python
"""Subsystem package — Local DM dispatch consumers.

Each subsystem is an async callable taking (dispatch: SubsystemDispatch,
**context) -> SubsystemOutput. The registry maps subsystem names to
callables. run_dispatch_bank executes a full DispatchPackage's worth
of dispatches, respecting depends_on and idempotency keys.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sidequest.protocol.dispatch import (
    DispatchPackage,
    NarratorDirective,
    SubsystemDispatch,
)

logger = logging.getLogger(__name__)

SubsystemCallable = Callable[..., Awaitable["SubsystemOutput"]]


@dataclass
class SubsystemOutput:
    directives: list[NarratorDirective] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class BankResult:
    """Result of executing a DispatchPackage's subsystem bank."""

    directives: list[NarratorDirective] = field(default_factory=list)
    outputs_by_key: dict[str, SubsystemOutput] = field(default_factory=dict)
    errors: list[tuple[str, str]] = field(default_factory=list)  # (idempotency_key, error_repr)


# Registry is populated at import time in _register_defaults().
_REGISTRY: dict[str, SubsystemCallable] = {}


def register_subsystem(name: str, fn: SubsystemCallable) -> None:
    if name in _REGISTRY:
        raise ValueError(f"subsystem already registered: {name}")
    _REGISTRY[name] = fn


def get_registered() -> dict[str, SubsystemCallable]:
    return dict(_REGISTRY)


def _register_defaults() -> None:
    from sidequest.agents.subsystems.distinctive_detail import run_distinctive_detail
    from sidequest.agents.subsystems.npc_agency import run_npc_agency
    from sidequest.agents.subsystems.reflect_absence import run_reflect_absence

    # Unregister-then-register to keep this import idempotent across test reloads.
    for name, fn in (
        ("reflect_absence", run_reflect_absence),
        ("distinctive_detail_hint", run_distinctive_detail),
        ("npc_agency", run_npc_agency),
    ):
        _REGISTRY.pop(name, None)
        _REGISTRY[name] = fn


_register_defaults()


def _topo_sort(dispatches: list[SubsystemDispatch]) -> list[SubsystemDispatch]:
    by_key = {d.idempotency_key: d for d in dispatches}
    order: list[SubsystemDispatch] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(key: str) -> None:
        if key in visited:
            return
        if key in visiting:
            raise ValueError(f"cycle in depends_on involving {key}")
        if key not in by_key:
            # depends_on referencing a key outside this bank — ignore gracefully.
            visited.add(key)
            return
        visiting.add(key)
        for dep in by_key[key].depends_on:
            visit(dep)
        visiting.remove(key)
        visited.add(key)
        order.append(by_key[key])

    for d in dispatches:
        visit(d.idempotency_key)
    return order


async def run_dispatch_bank(
    package: DispatchPackage,
    *,
    context: dict[str, Any] | None = None,
) -> BankResult:
    """Execute every SubsystemDispatch in the package.

    Runs sequentially in topological order (Group B simplification; spec §8
    allows parallel within a serialization layer, added in Group C as
    subsystem volume grows). Unknown subsystems are logged and skipped.
    Exceptions are caught per-dispatch and logged; never re-raised.
    """
    context = context or {}
    result = BankResult()

    all_dispatches: list[SubsystemDispatch] = []
    for pd in package.per_player:
        all_dispatches.extend(pd.dispatch)
    for ca in package.cross_player:
        all_dispatches.extend(ca.dispatch)

    if not all_dispatches:
        return result

    try:
        ordered = _topo_sort(all_dispatches)
    except ValueError as exc:
        logger.error("subsystems.bank_topo_sort_failed exc=%s", exc)
        # If topo sort fails, run in declaration order — better than dropping.
        ordered = all_dispatches

    seen: set[str] = set()
    for d in ordered:
        if d.idempotency_key in seen:
            continue
        seen.add(d.idempotency_key)

        fn = _REGISTRY.get(d.subsystem)
        if fn is None:
            logger.warning("subsystems.unknown subsystem=%s key=%s", d.subsystem, d.idempotency_key)
            continue
        try:
            out = await fn(d, **context)
        except Exception as exc:  # subsystem bug or missing context kwarg
            logger.warning(
                "subsystems.dispatch_failed subsystem=%s key=%s exc=%s",
                d.subsystem, d.idempotency_key, exc,
            )
            result.errors.append((d.idempotency_key, repr(exc)))
            continue

        result.outputs_by_key[d.idempotency_key] = out
        result.directives.extend(out.directives)

    # Also include any decomposer-authored directives in per_player[].narrator_instructions
    # so the narrator receives them even if no subsystem produced equivalent output.
    for pd in package.per_player:
        result.directives.extend(pd.narrator_instructions)

    return result


__all__ = [
    "BankResult",
    "SubsystemCallable",
    "SubsystemOutput",
    "get_registered",
    "register_subsystem",
    "run_dispatch_bank",
]
```

- [ ] **Step 2: Write the failing test**

Create `tests/agents/test_subsystem_registry.py`:

```python
"""Tests for the subsystem registry and dispatch bank executor."""
from __future__ import annotations

import pytest

from sidequest.agents.subsystems import (
    SubsystemOutput,
    get_registered,
    run_dispatch_bank,
)
from sidequest.protocol.dispatch import (
    DispatchPackage,
    NarratorDirective,
    PlayerDispatch,
    SubsystemDispatch,
    VisibilityTag,
)


def _tag_all() -> VisibilityTag:
    return VisibilityTag(
        visible_to="all", perception_fidelity={}, secrets_for=[],
        redact_from_narrator_canonical=False,
    )


def _make_dispatch(name: str, key: str, *, depends_on=(), params=None) -> SubsystemDispatch:
    return SubsystemDispatch(
        subsystem=name,
        params=params or {},
        depends_on=list(depends_on),
        idempotency_key=key,
        visibility=_tag_all(),
    )


def _make_package(per_player_dispatches: list[list[SubsystemDispatch]]) -> DispatchPackage:
    return DispatchPackage(
        turn_id="t",
        per_player=[
            PlayerDispatch(
                player_id=f"player:P{i}",
                raw_action="",
                resolved=[],
                dispatch=dispatches,
                lethality=[],
                narrator_instructions=[],
            )
            for i, dispatches in enumerate(per_player_dispatches)
        ],
        cross_player=[],
        confidence_global=1.0,
        degraded=False,
        degraded_reason=None,
    )


def test_defaults_are_registered():
    registered = get_registered()
    assert {"reflect_absence", "distinctive_detail_hint", "npc_agency"} <= set(registered.keys())


@pytest.mark.asyncio
async def test_run_dispatch_bank_reflect_absence_produces_directives():
    pkg = _make_package([[_make_dispatch("reflect_absence", "k1")]])
    res = await run_dispatch_bank(pkg)
    kinds = {d.kind for d in res.directives}
    assert {"must_not_narrate", "must_narrate"} <= kinds
    assert "k1" in res.outputs_by_key


@pytest.mark.asyncio
async def test_run_dispatch_bank_unknown_subsystem_is_skipped():
    pkg = _make_package([[_make_dispatch("not_a_real_subsystem", "k1")]])
    res = await run_dispatch_bank(pkg)
    assert res.directives == []
    assert res.outputs_by_key == {}
    assert res.errors == []  # unknown is skip, not error


@pytest.mark.asyncio
async def test_run_dispatch_bank_idempotency_key_dedupes():
    dup = _make_dispatch("reflect_absence", "same_key")
    pkg = _make_package([[dup, dup]])
    # Pydantic model_validator rejects duplicate keys; use construct to bypass for test.
    pkg.per_player[0].dispatch = [dup, dup]
    res = await run_dispatch_bank(pkg)
    assert len(res.outputs_by_key) == 1


@pytest.mark.asyncio
async def test_run_dispatch_bank_topo_sort_respects_depends_on():
    a = _make_dispatch("reflect_absence", "A")
    b = _make_dispatch("reflect_absence", "B", depends_on=["A"])
    pkg = _make_package([[b, a]])  # declared out of order
    res = await run_dispatch_bank(pkg)
    # Both ran.
    assert set(res.outputs_by_key.keys()) == {"A", "B"}


@pytest.mark.asyncio
async def test_run_dispatch_bank_directives_include_decomposer_authored():
    """Narrator_instructions authored directly by the decomposer (not via subsystem)
    still reach the final directive list."""
    pkg = DispatchPackage(
        turn_id="t",
        per_player=[PlayerDispatch(
            player_id="player:P0",
            raw_action="",
            resolved=[],
            dispatch=[],
            lethality=[],
            narrator_instructions=[NarratorDirective(
                kind="must_narrate", payload="a thing", visibility=_tag_all(),
            )],
        )],
        cross_player=[],
        confidence_global=1.0,
        degraded=False,
        degraded_reason=None,
    )
    res = await run_dispatch_bank(pkg)
    payloads = [d.payload for d in res.directives]
    assert "a thing" in payloads


@pytest.mark.asyncio
async def test_run_dispatch_bank_subsystem_exception_is_caught():
    """A subsystem raising inside the bank logs and continues."""
    # distinctive_detail raises ValueError when target missing.
    d = _make_dispatch("distinctive_detail_hint", "k_err", params={"hint": "x"})  # no target
    pkg = _make_package([[d]])
    res = await run_dispatch_bank(pkg)
    assert len(res.errors) == 1
    assert res.errors[0][0] == "k_err"
    # No directives from the failing subsystem.
    assert all(dd.payload != "x" for dd in res.directives)


@pytest.mark.asyncio
async def test_run_dispatch_bank_threads_context_to_subsystems(minimal_npc_registry):
    """npc_agency receives npc_registry via context kwargs."""
    d = _make_dispatch(
        "npc_agency", "k1",
        params={"npc_name": "Harlan", "situation": "spotted"},
    )
    pkg = _make_package([[d]])
    res = await run_dispatch_bank(pkg, context={"npc_registry": minimal_npc_registry})
    out: SubsystemOutput = res.outputs_by_key["k1"]
    assert out.data["role"] == "innkeeper"
```

Add a top-level `conftest.py` entry re-exposing the `minimal_npc_registry` fixture from `tests/agents/subsystems/conftest.py`, or move that fixture up to `tests/agents/conftest.py` so both test files see it.

- [ ] **Step 3: Run — verify pass (registry + helpers were implemented in Step 1 alongside the test, so this task is TDD-reversed by design since registry infra exists before test uses it)**

```bash
uv run pytest tests/agents/test_subsystem_registry.py -v 2>&1 | tail -30
```

Expected: all 8 tests pass.

- [ ] **Step 4: Commit**

```bash
git add sidequest/agents/subsystems/__init__.py tests/agents/test_subsystem_registry.py tests/agents/conftest.py
git commit -m "feat(subsystems): registry + dispatch-bank executor with topo sort (group B task 7)"
```

---

## Task 8: Extend `TurnContext` to carry `DispatchPackage`

**Files:**
- Modify: `sidequest/agents/orchestrator.py` (the `TurnContext` dataclass near line ~230)
- Modify: existing `TurnContext` tests (if any) to exercise the new field default

**Context:** `TurnContext` is the state bag passed into `run_narration_turn`. Add an optional `dispatch_package: DispatchPackage | None = None` field. Default is `None`, which means "no decomposer ran" — the narrator behaves as today. The session handler (Task 10) populates it. The orchestrator (Task 9) consumes it.

Keep the change minimal: new optional field, default `None`, import the type, tests confirm default + populated shape.

- [ ] **Step 1: Locate the `TurnContext` definition**

```bash
grep -n "class TurnContext\|@dataclass" /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b/sidequest/agents/orchestrator.py | head -10
```

Expected: a `class TurnContext` line around ~230 (line may drift post-Group-A).

- [ ] **Step 2: Write a failing test — `TurnContext` accepts `dispatch_package`**

Create or append to `tests/agents/test_orchestrator.py`:

```python
"""Tests for TurnContext post-Group-B extension."""
from sidequest.agents.orchestrator import TurnContext
from sidequest.protocol.dispatch import DispatchPackage


def test_turn_context_defaults_dispatch_package_to_none():
    tc = TurnContext()  # whatever defaults are valid pre-Group-B
    assert getattr(tc, "dispatch_package", "missing") is None


def test_turn_context_accepts_dispatch_package():
    pkg = DispatchPackage(
        turn_id="t1", per_player=[], cross_player=[],
        confidence_global=1.0, degraded=False, degraded_reason=None,
    )
    tc = TurnContext(dispatch_package=pkg)
    assert tc.dispatch_package is pkg
```

> **If `TurnContext()` with no args is invalid (other required fields exist), supply minimal valid values from the existing constructor.** Read the current class first.

- [ ] **Step 3: Run — verify fail**

```bash
uv run pytest tests/agents/test_orchestrator.py -k "dispatch_package" -v 2>&1 | tail -10
```

Expected: `AttributeError: 'TurnContext' has no attribute 'dispatch_package'` or `TypeError: __init__() got an unexpected keyword argument`.

- [ ] **Step 4: Add `dispatch_package` field to `TurnContext`**

In `sidequest/agents/orchestrator.py`, add the import:

```python
from sidequest.protocol.dispatch import DispatchPackage
```

And in the `TurnContext` dataclass, after the last existing field, add:

```python
    # Group B (Local DM decomposer) — session handler populates before calling
    # run_narration_turn. Consumed by build_narrator_prompt to register the
    # narrator_directives PromptSection. Default None = decomposer did not run.
    dispatch_package: DispatchPackage | None = None
```

- [ ] **Step 5: Run — verify pass**

```bash
uv run pytest tests/agents/test_orchestrator.py -k "dispatch_package" -v 2>&1 | tail -10
```

Expected: 2 passed. Also run the full file to confirm nothing else broke:

```bash
uv run pytest tests/agents/test_orchestrator.py -v 2>&1 | tail -5
```

- [ ] **Step 6: Commit**

```bash
git add sidequest/agents/orchestrator.py tests/agents/test_orchestrator.py
git commit -m "feat(agents): TurnContext carries DispatchPackage (group B task 8)"
```

---

## Task 9: Register `narrator_directives` PromptSection when `dispatch_package` present

**Files:**
- Modify: `sidequest/agents/orchestrator.py` — `build_narrator_prompt` (near line ~1000)
- Modify/Create: `tests/agents/test_orchestrator.py`

**Context:** When a `DispatchPackage` is attached to `TurnContext`, format its subsystem-produced directives + decomposer-authored `narrator_instructions` into a block and register it as a `PromptSection("narrator_directives", ...)` at `AttentionZone.Fovea` (directives are load-bearing, not ambient context).

We run the subsystem bank here (not in session handler) because the prompt builder is where the injection happens — and the bank's output is *narrator prompt content*. The session handler (Task 10) will decide what NPC registry / context to pass.

Group B does **not** yet write subsystem state deltas back into the snapshot (state-writing subsystems arrive with Group C confrontation). The bank's `data` output is collected but unused in Group B except for logging.

- [ ] **Step 1: Read the current `build_narrator_prompt` for the registry pattern**

```bash
grep -n "build_narrator_prompt\|register_section\|AttentionZone\|PromptSection" /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b/sidequest/agents/orchestrator.py | head -30
```

Identify the exact place sections are registered (existing `world_context`, `retrieved_lore`, `active_tropes` sections around line 1020–1060).

- [ ] **Step 2: Write the failing test**

Append to `tests/agents/test_orchestrator.py`:

```python
import pytest

from sidequest.agents.orchestrator import Orchestrator
from sidequest.protocol.dispatch import (
    DispatchPackage,
    NarratorDirective,
    PlayerDispatch,
    VisibilityTag,
)


def _tag_all() -> VisibilityTag:
    return VisibilityTag(
        visible_to="all", perception_fidelity={}, secrets_for=[],
        redact_from_narrator_canonical=False,
    )


@pytest.mark.asyncio
async def test_build_narrator_prompt_registers_narrator_directives_when_present():
    """When TurnContext has a dispatch_package with directives, the prompt
    registry contains a 'narrator_directives' section at Fovea."""
    orch = Orchestrator()  # uses default stub client — don't invoke LLM here
    pkg = DispatchPackage(
        turn_id="t1",
        per_player=[PlayerDispatch(
            player_id="player:Alice",
            raw_action="Let's go!",
            resolved=[],
            dispatch=[],
            lethality=[],
            narrator_instructions=[
                NarratorDirective(kind="must_not_narrate",
                                  payload="inventing a follower", visibility=_tag_all()),
                NarratorDirective(kind="must_narrate",
                                  payload="the empty room", visibility=_tag_all()),
            ],
        )],
        cross_player=[],
        confidence_global=1.0,
        degraded=False,
        degraded_reason=None,
    )
    # Construct a minimal-valid TurnContext; fill in real required fields
    # from the actual class.
    ctx = _build_minimal_turn_context_with_dispatch(pkg)

    prompt_text, registry = orch.build_narrator_prompt("Let's go!", ctx, tier=orch.select_prompt_tier(ctx))

    names = [s.name for s in registry.sections_for(orch._narrator.name())]
    assert "narrator_directives" in names
    # Payload strings appear in the rendered prompt.
    assert "inventing a follower" in prompt_text
    assert "the empty room" in prompt_text


def test_build_narrator_prompt_omits_narrator_directives_when_no_dispatch_package():
    orch = Orchestrator()
    ctx = _build_minimal_turn_context_without_dispatch()
    prompt_text, registry = orch.build_narrator_prompt("look around", ctx, tier=orch.select_prompt_tier(ctx))
    names = [s.name for s in registry.sections_for(orch._narrator.name())]
    assert "narrator_directives" not in names
```

> **`_build_minimal_turn_context_with_dispatch` and `_build_minimal_turn_context_without_dispatch` are local helpers — define them at the top of the test file using whatever real `TurnContext` fields are required. If existing orchestrator tests already have a helper, reuse it.** Also check whether the `registry.sections_for(...)` accessor exists; if the test registry exposes sections differently, adapt.

- [ ] **Step 3: Run — verify fail**

```bash
uv run pytest tests/agents/test_orchestrator.py -k "narrator_directives" -v 2>&1 | tail -15
```

Expected: test fails because the section isn't registered.

- [ ] **Step 4: Implement**

In `sidequest/agents/orchestrator.py::Orchestrator.build_narrator_prompt`, after the `active_tropes` registration block (~line 1060), add:

```python
        # Group B — Local DM decomposer narrator_directives (Fovea zone).
        # When the decomposer ran, run its dispatch bank here and inject the
        # aggregated directives as a high-attention section.
        if context.dispatch_package is not None:
            from sidequest.agents.subsystems import run_dispatch_bank

            bank_context: dict[str, object] = {}
            npc_registry = getattr(context, "npc_registry", None)
            if npc_registry is not None:
                bank_context["npc_registry"] = npc_registry

            bank_result = await run_dispatch_bank(context.dispatch_package, context=bank_context)
            if bank_result.directives:
                block = "\n".join(
                    f"- [{d.kind}] {d.payload}" for d in bank_result.directives
                )
                registry.register_section(
                    agent_name,
                    PromptSection.new(
                        "narrator_directives",
                        block,
                        AttentionZone.Fovea,
                        SectionCategory.State,
                    ),
                )
            # Surface subsystem errors in a log line for GM-panel consumption via OTEL.
            for key, err in bank_result.errors:
                logger.warning("orchestrator.subsystem_error key=%s error=%s", key, err)
```

Important: `build_narrator_prompt` needs to become `async` if it isn't already, since `run_dispatch_bank` is async. If it's currently sync, choose one:
- **Option A (preferred)**: make `build_narrator_prompt` async and update the single caller in `run_narration_turn` to `await` it.
- **Option B (fallback if widely sync-called)**: run the bank in `run_narration_turn` instead and pass the `BankResult.directives` into `build_narrator_prompt` via a new keyword.

Check the one caller:

```bash
grep -n "build_narrator_prompt" /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b/sidequest/agents/orchestrator.py
```

If only used in one place (`run_narration_turn`, which is already async), Option A is clean.

- [ ] **Step 5: Run — verify pass**

```bash
uv run pytest tests/agents/test_orchestrator.py -v 2>&1 | tail -20
```

Expected: new tests pass; no regression on existing tests.

- [ ] **Step 6: Commit**

```bash
git add sidequest/agents/orchestrator.py tests/agents/test_orchestrator.py
git commit -m "feat(agents): inject narrator_directives from DispatchPackage (group B task 9)"
```

---

## Task 10: Wire `LocalDM.decompose` into `_execute_narration_turn`

**Files:**
- Modify: `sidequest/server/session_handler.py::_execute_narration_turn` (line ~1673)
- Modify/Create: `tests/server/test_session_handler_decomposer.py`

**Context:** The session handler is where we mount the decomposer between sealed-letter completion and the narrator call. In Group B the path is single-player (one `raw_action`), so we call `LocalDM.decompose(...)` with that one action and attach the resulting package to `TurnContext`.

Structural changes to `_execute_narration_turn`:

1. Lazy-construct a `LocalDM` instance bound to the session (one instance per session; persists across turns for ADR-066 session reuse).
2. Before `orchestrator.run_narration_turn`, call `local_dm.decompose(...)` and attach the result to `turn_context.dispatch_package`.
3. Also attach `turn_context.npc_registry = sd.snapshot.npc_registry` (or equivalent) so the `npc_agency` subsystem can look up NPCs.
4. If the decomposer returned `degraded=True`, log it as `session.decomposer_degraded` but proceed — the narrator still runs.

The `LocalDM` instance needs to outlive a single turn to benefit from ADR-066 session resume. Add `local_dm: LocalDM` to `_SessionData` (or equivalent session-scoped struct).

- [ ] **Step 1: Locate `_SessionData` and session construction**

```bash
grep -n "class _SessionData\|@dataclass" /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b/sidequest/server/session_handler.py | head -10
```

Confirm the struct + where it's initialized (look for `_SessionData(` constructor calls, probably in session-open or genre-bind paths).

- [ ] **Step 2: Write the failing wiring test**

Create `tests/server/test_session_handler_decomposer.py`:

```python
"""Wiring test — LocalDM runs between sealed-letter and narrator in the session handler."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_execute_narration_turn_invokes_local_dm_before_narrator(session_fixture):
    """The session handler calls LocalDM.decompose exactly once before
    orchestrator.run_narration_turn, and attaches the result to TurnContext."""
    sd, handler = session_fixture  # sets up a minimal session with genre pack

    captured: dict = {}

    async def fake_decompose(**kwargs):
        from sidequest.protocol.dispatch import DispatchPackage
        captured["decomposer_called"] = True
        captured["raw_action"] = kwargs["raw_action"]
        return DispatchPackage(
            turn_id=kwargs["turn_id"], per_player=[], cross_player=[],
            confidence_global=1.0, degraded=False, degraded_reason=None,
        )

    async def fake_run_narration_turn(action, context):
        captured["narrator_called"] = True
        captured["narrator_saw_dispatch_package"] = context.dispatch_package is not None
        # Before writing this, grep the real NarrationTurnResult dataclass (line
        # ~177 of sidequest/agents/orchestrator.py) for its full field list and
        # default values — reuse the existing test helper if one is present:
        #   grep -rn "NarrationTurnResult(" tests/ --include="*.py" | head -5
        # Then replicate the minimal-valid kwargs here.
        from sidequest.agents.orchestrator import NarrationTurnResult
        return _make_minimal_narration_turn_result(narration="ok")

    with patch.object(sd.local_dm, "decompose", side_effect=fake_decompose), \
         patch.object(sd.orchestrator, "run_narration_turn", side_effect=fake_run_narration_turn):
        await handler._execute_narration_turn(sd, "I look around.", _build_turn_context_for_test(sd))

    assert captured["decomposer_called"] is True
    assert captured["narrator_called"] is True
    assert captured["raw_action"] == "I look around."
    assert captured["narrator_saw_dispatch_package"] is True


@pytest.mark.asyncio
async def test_execute_narration_turn_continues_when_decomposer_degraded(session_fixture):
    """A degraded decomposer package does not abort the turn."""
    sd, handler = session_fixture

    async def degraded_decompose(**kwargs):
        from sidequest.protocol.dispatch import DispatchPackage
        return DispatchPackage(
            turn_id=kwargs["turn_id"], per_player=[], cross_player=[],
            confidence_global=0.0, degraded=True, degraded_reason="test-forced",
        )

    narrator_called = False
    async def fake_run(action, context):
        nonlocal narrator_called
        narrator_called = True
        return _make_minimal_narration_turn_result(narration="ok")

    with patch.object(sd.local_dm, "decompose", side_effect=degraded_decompose), \
         patch.object(sd.orchestrator, "run_narration_turn", side_effect=fake_run):
        await handler._execute_narration_turn(sd, "x", _build_turn_context_for_test(sd))

    assert narrator_called, "narrator must still run when decomposer is degraded"
```

The `session_fixture` and `_build_turn_context_for_test` helpers need to be defined once in a shared conftest for these tests. First discover existing server-test fixtures:

```bash
grep -rn "def.*session.*fixture\|@pytest.fixture" /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b/tests/server/ --include="*.py" | head -10
```

Reuse the closest existing fixture that builds a `_SessionData` (probably in a smoke-test module). Add these to `tests/server/conftest.py` (creating it if absent):

```python
import pytest

from sidequest.agents.orchestrator import TurnContext


@pytest.fixture
def session_fixture(existing_session_builder):
    """Return (sd, handler) — a minimal in-memory session + its handler.

    existing_session_builder is whatever the closest smoke-test fixture
    provides; swap in its real name.
    """
    sd = existing_session_builder()
    handler = sd.handler  # or however the handler is exposed
    return sd, handler


def _build_turn_context_for_test(sd) -> TurnContext:
    """Minimal TurnContext populated from session state — fields not under test
    take their dataclass defaults."""
    return TurnContext(
        state_summary=sd.snapshot.get_state_summary() if hasattr(sd.snapshot, "get_state_summary") else "",
        genre=sd.genre_slug,
        character_name=sd.player_name,
        current_location=getattr(sd.snapshot, "current_location", "Unknown"),
        npc_registry=list(getattr(sd.snapshot, "npc_registry", [])),
    )
```

Also define a `_make_minimal_narration_turn_result` helper here. First discover what fields `NarrationTurnResult` requires:

```bash
sed -n '175,215p' /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b/sidequest/agents/orchestrator.py
```

Then:

```python
def _make_minimal_narration_turn_result(narration: str = "ok", is_degraded: bool = False):
    """Construct a NarrationTurnResult with minimal valid kwargs.

    Fill in every non-defaulted field per the real dataclass signature.
    Tests should not care about content — only that the type checks.
    """
    from sidequest.agents.orchestrator import NarrationTurnResult
    return NarrationTurnResult(
        narration=narration,
        is_degraded=is_degraded,
        agent_duration_ms=1,
        # + any additional required fields discovered via the grep above
    )
```

Adapt the internals to whatever the real `_SessionData` + snapshot expose — the point is that all three helpers (`session_fixture`, `_build_turn_context_for_test`, `_make_minimal_narration_turn_result`) are defined *once* here and imported by every test in this file.

- [ ] **Step 3: Run — verify fail**

```bash
uv run pytest tests/server/test_session_handler_decomposer.py -v 2>&1 | tail -15
```

Expected: fails with `AttributeError: '_SessionData' object has no attribute 'local_dm'` (or equivalent — the handler isn't calling `decompose`).

- [ ] **Step 4: Add `local_dm` to `_SessionData` and wire into `_execute_narration_turn`**

In `sidequest/server/session_handler.py`:

a. Import `LocalDM` near other agent imports:

```python
from sidequest.agents.local_dm import LocalDM
```

b. Add a `local_dm: LocalDM` field to `_SessionData` with a default (factory if it's a dataclass):

```python
    local_dm: LocalDM = field(default_factory=LocalDM)
```

c. In `_execute_narration_turn`, before line 1690 (`with orchestrator_process_action_span...`), insert:

```python
        # Group B — Local DM decomposer runs between sealed-letter and narrator.
        turn_id = f"{sd.genre_slug}:{sd.world_slug}:{snapshot.turn_manager.interaction}"
        state_summary = turn_context.state_summary if hasattr(turn_context, "state_summary") else ""
        try:
            dispatch_package = await sd.local_dm.decompose(
                turn_id=turn_id,
                player_id=f"player:{sd.player_name}",
                raw_action=action,
                state_summary=state_summary,
            )
        except Exception as exc:
            logger.warning("session.decomposer_exception exc=%s", exc)
            from sidequest.protocol.dispatch import DispatchPackage
            dispatch_package = DispatchPackage(
                turn_id=turn_id, per_player=[], cross_player=[],
                confidence_global=0.0, degraded=True,
                degraded_reason=f"exception: {exc}",
            )
        if dispatch_package.degraded:
            logger.info(
                "session.decomposer_degraded reason=%s turn_id=%s",
                dispatch_package.degraded_reason, turn_id,
            )
        turn_context.dispatch_package = dispatch_package
        # turn_context.npc_registry is already a field on TurnContext and is
        # populated by _build_turn_context. We rely on that existing value —
        # do NOT overwrite it here. The orchestrator reads it in Task 9.
```

d. Confirm the `state_summary` field name on `TurnContext` — it is the field at line ~243 of `orchestrator.py` (`state_summary: str | None = None`) used in `build_narrator_prompt` injection around line 1030.

e. `TurnContext.npc_registry: list[NpcRegistryEntry]` already exists (line ~310 of `orchestrator.py`). No new field is needed — the existing one is what the `npc_agency` subsystem consumes via the Task 9 wiring.

- [ ] **Step 5: Run — verify pass**

```bash
uv run pytest tests/server/test_session_handler_decomposer.py -v 2>&1 | tail -15
```

Expected: both wiring tests pass.

- [ ] **Step 6: Commit**

```bash
git add sidequest/server/session_handler.py sidequest/agents/orchestrator.py tests/server/test_session_handler_decomposer.py
git commit -m "feat(server): LocalDM runs between sealed-letter and narrator (group B task 10)"
```

---

## Task 11: Add OTEL spans for decomposer + subsystems

**Files:**
- Modify: `sidequest/telemetry/spans.py` (add constants + helpers)
- Modify: `sidequest/agents/local_dm.py` (wrap decompose in span)
- Modify: `sidequest/agents/subsystems/__init__.py` (wrap each dispatch in span)
- Modify: `tests/agents/test_local_dm.py`, `tests/agents/test_subsystem_registry.py` (assert spans fire)

**Context:** The GM panel is the lie detector for Claude hallucinations (CLAUDE.md OTEL principle). Every decomposer + subsystem call must emit a span so Sebastien (mechanical-first player, GM-panel audience) can see what ran. Use the existing `tracer()` + `start_as_current_span` pattern — three new span names:

- `local_dm.decompose` — whole decomposer call
- `local_dm.dispatch_bank` — bank executor
- `local_dm.subsystem` — one per subsystem invocation, with `attributes["subsystem"]`

Tests use the **provider-local tracer injection** pattern seen in `spans.py:259` helpers to avoid fighting OpenTelemetry's single-provider-per-process rule — existing helpers accept `_tracer=` for that reason.

- [ ] **Step 1: Extend `sidequest/telemetry/spans.py`**

Append constants after the existing SPAN_ group:

```python
# ---------------------------------------------------------------------------
# Local DM (Group B) — decomposer + subsystem bank
# ---------------------------------------------------------------------------
SPAN_LOCAL_DM_DECOMPOSE = "local_dm.decompose"
SPAN_LOCAL_DM_DISPATCH_BANK = "local_dm.dispatch_bank"
SPAN_LOCAL_DM_SUBSYSTEM = "local_dm.subsystem"
```

And context-manager helpers at the bottom alongside the existing helpers:

```python
@contextmanager
def local_dm_decompose_span(
    turn_id: str, player_id: str, action_len: int,
    *, _tracer: trace.Tracer | None = None, **attrs: Any,
) -> Iterator[trace.Span]:
    t = _tracer if _tracer is not None else tracer()
    with t.start_as_current_span(
        SPAN_LOCAL_DM_DECOMPOSE,
        attributes={"turn_id": turn_id, "player_id": player_id, "action_len": action_len, **attrs},
    ) as span:
        yield span


@contextmanager
def local_dm_dispatch_bank_span(
    turn_id: str, dispatch_count: int,
    *, _tracer: trace.Tracer | None = None, **attrs: Any,
) -> Iterator[trace.Span]:
    t = _tracer if _tracer is not None else tracer()
    with t.start_as_current_span(
        SPAN_LOCAL_DM_DISPATCH_BANK,
        attributes={"turn_id": turn_id, "dispatch_count": dispatch_count, **attrs},
    ) as span:
        yield span


@contextmanager
def local_dm_subsystem_span(
    subsystem: str, idempotency_key: str,
    *, _tracer: trace.Tracer | None = None, **attrs: Any,
) -> Iterator[trace.Span]:
    t = _tracer if _tracer is not None else tracer()
    with t.start_as_current_span(
        SPAN_LOCAL_DM_SUBSYSTEM,
        attributes={"subsystem": subsystem, "idempotency_key": idempotency_key, **attrs},
    ) as span:
        yield span
```

- [ ] **Step 2: Wrap `LocalDM.decompose` in `local_dm_decompose_span`**

In `sidequest/agents/local_dm.py`, import the helper and wrap the method body:

```python
from sidequest.telemetry.spans import local_dm_decompose_span
```

Wrap the body of `decompose`:

```python
    async def decompose(self, *, turn_id, player_id, raw_action, state_summary):
        with local_dm_decompose_span(
            turn_id=turn_id, player_id=player_id, action_len=len(raw_action),
        ) as span:
            # ... existing body ...
            # Before returning, annotate the span with the outcome:
            span.set_attribute("degraded", pkg.degraded)
            if pkg.degraded:
                span.set_attribute("degraded_reason", pkg.degraded_reason or "")
            return pkg
```

- [ ] **Step 3: Wrap bank + each subsystem in spans**

In `sidequest/agents/subsystems/__init__.py::run_dispatch_bank`:

```python
from sidequest.telemetry.spans import local_dm_dispatch_bank_span, local_dm_subsystem_span

# At the top of run_dispatch_bank:
with local_dm_dispatch_bank_span(
    turn_id=package.turn_id, dispatch_count=len(all_dispatches),
):
    # ... existing body ...
    for d in ordered:
        with local_dm_subsystem_span(
            subsystem=d.subsystem, idempotency_key=d.idempotency_key,
        ) as span:
            # ... existing per-dispatch body ...
            span.set_attribute("produced_directives", len(out.directives) if 'out' in dir() else 0)
```

Check indentation carefully — the `with` wraps an existing body; don't accidentally re-scope variables.

- [ ] **Step 4: Write / extend tests to assert spans fire**

Add to `tests/agents/test_local_dm.py`:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


@pytest.fixture
def span_recorder():
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    # Return exporter + local tracer so we don't mutate global state.
    yield exporter, provider.get_tracer("test")


@pytest.mark.asyncio
async def test_local_dm_emits_decompose_span(dispatch_json_absence, span_recorder, monkeypatch):
    exporter, local_tracer = span_recorder
    # Patch tracer() to return the local one.
    from sidequest.telemetry import setup as telemetry_setup
    monkeypatch.setattr(telemetry_setup, "tracer", lambda: local_tracer)

    client = _make_mock_client(dispatch_json_absence)
    dm = LocalDM(client=client)
    await dm.decompose(
        turn_id="turn-span", player_id="player:Alice",
        raw_action="x", state_summary="y",
    )

    spans = exporter.get_finished_spans()
    names = [s.name for s in spans]
    assert "local_dm.decompose" in names
```

Add an equivalent test in `test_subsystem_registry.py` asserting `local_dm.dispatch_bank` and `local_dm.subsystem` spans fire.

- [ ] **Step 5: Run — verify pass**

```bash
uv run pytest tests/agents/test_local_dm.py tests/agents/test_subsystem_registry.py -v 2>&1 | tail -20
```

Expected: all pass. Span-count assertions will catch a missing wrap.

- [ ] **Step 6: Commit**

```bash
git add sidequest/telemetry/spans.py sidequest/agents/local_dm.py sidequest/agents/subsystems/__init__.py tests/agents/test_local_dm.py tests/agents/test_subsystem_registry.py
git commit -m "feat(telemetry): OTEL spans for decomposer + subsystem bank (group B task 11)"
```

---

## Task 12: Integration test — happy path (pronoun resolved cleanly)

**Files:**
- Modify: `tests/server/test_session_handler_decomposer.py`

**Context:** End-to-end against the session handler with a mocked Haiku returning a clean resolution. Verify the narrator prompt contains a `distinctive_detail_for_referent` directive payload mentioning the picked target.

- [ ] **Step 1: Append to `tests/server/test_session_handler_decomposer.py`**

```python
@pytest.mark.asyncio
async def test_full_turn_happy_path_pronoun_resolved(session_fixture, dispatch_json_pronoun_resolved):
    """Decomposer returns a clean resolution; narrator prompt carries the
    distinctive_detail directive; no degraded flag."""
    sd, handler = session_fixture

    # Make sd.local_dm's underlying client return the fixture response.
    from unittest.mock import AsyncMock, patch
    from sidequest.agents.claude_client import ClaudeResponse

    sd.local_dm._client = AsyncMock()
    sd.local_dm._client.send_with_session = AsyncMock(return_value=ClaudeResponse(
        text=dispatch_json_pronoun_resolved, session_id="dec-sess-xyz", stop_reason="end_turn",
    ))

    # Capture the final narrator prompt for inspection.
    captured_prompt = {}
    orig_build = sd.orchestrator.build_narrator_prompt
    async def spying_build(action, context, *, tier):
        prompt_text, registry = await orig_build(action, context, tier=tier)
        captured_prompt["text"] = prompt_text
        return prompt_text, registry

    sd.orchestrator.build_narrator_prompt = spying_build

    # Stub out the actual Claude narrator call.
    async def fake_narrator_call(*args, **kwargs):
        return ClaudeResponse(text='{"narration": "ok"}', session_id="n", stop_reason="end_turn")
    sd.orchestrator._client = AsyncMock()
    sd.orchestrator._client.send_with_session = AsyncMock(side_effect=fake_narrator_call)

    await handler._execute_narration_turn(sd, "Attack him!", _build_turn_context_for_test(sd))

    assert "text" in captured_prompt
    prompt_text = captured_prompt["text"]
    assert "distinctive_detail_for_referent" in prompt_text or "broken tooth" in prompt_text
```

- [ ] **Step 2: Run — verify pass (or fail + fix if state threading missed a field)**

```bash
uv run pytest tests/server/test_session_handler_decomposer.py -v 2>&1 | tail -15
```

- [ ] **Step 3: Commit**

```bash
git add tests/server/test_session_handler_decomposer.py
git commit -m "test: integration — happy path pronoun resolution (group B task 12)"
```

---

## Task 13: Integration test — absence path (`"Let's go!"` with no party)

**Files:**
- Modify: `tests/server/test_session_handler_decomposer.py`

**Context:** Spec §6.3. Haiku returns a `reflect_absence` dispatch; narrator prompt contains `must_not_narrate` + `must_narrate` directives.

- [ ] **Step 1: Append the test**

```python
@pytest.mark.asyncio
async def test_full_turn_absence_path_injects_reflect_absence_directives(session_fixture, dispatch_json_absence):
    """Decomposer resolves 'let's' to absence; narrator prompt tells it not
    to invent a follower and to narrate the empty room."""
    sd, handler = session_fixture

    from unittest.mock import AsyncMock
    from sidequest.agents.claude_client import ClaudeResponse

    sd.local_dm._client = AsyncMock()
    sd.local_dm._client.send_with_session = AsyncMock(return_value=ClaudeResponse(
        text=dispatch_json_absence, session_id="dec-sess-xyz", stop_reason="end_turn",
    ))

    captured_prompt = {}
    orig_build = sd.orchestrator.build_narrator_prompt
    async def spying_build(action, context, *, tier):
        prompt_text, registry = await orig_build(action, context, tier=tier)
        captured_prompt["text"] = prompt_text
        return prompt_text, registry
    sd.orchestrator.build_narrator_prompt = spying_build

    sd.orchestrator._client = AsyncMock()
    sd.orchestrator._client.send_with_session = AsyncMock(return_value=ClaudeResponse(
        text='{"narration": "the room is empty"}', session_id="n", stop_reason="end_turn",
    ))

    await handler._execute_narration_turn(sd, "Let's go!", _build_turn_context_for_test(sd))

    prompt_text = captured_prompt["text"]
    assert "must_not_narrate" in prompt_text
    assert "must_narrate" in prompt_text
    assert "follower" in prompt_text.lower()  # reflect_absence must-not payload
    assert "empty" in prompt_text.lower()  # reflect_absence must-narrate payload
```

- [ ] **Step 2: Run**

```bash
uv run pytest tests/server/test_session_handler_decomposer.py -v 2>&1 | tail -10
```

Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add tests/server/test_session_handler_decomposer.py
git commit -m "test: integration — absence path reflect_absence directives (group B task 13)"
```

---

## Task 14: Integration test — degraded decomposer does not block the turn

**Files:**
- Modify: `tests/server/test_session_handler_decomposer.py`

**Context:** Spec §6.6 — if the decomposer times out or returns unparseable JSON, the narrator still runs on a minimal static injection. The earlier test in Task 10 covers the `degraded=True` explicit case; this one covers the *exception* path (network timeout).

- [ ] **Step 1: Append**

```python
@pytest.mark.asyncio
async def test_full_turn_decomposer_timeout_narrator_still_runs(session_fixture):
    """A TimeoutError inside LocalDM.decompose falls back to a degraded
    package; the narrator runs anyway and the turn completes."""
    sd, handler = session_fixture

    from unittest.mock import AsyncMock
    sd.local_dm._client = AsyncMock()
    sd.local_dm._client.send_with_session = AsyncMock(side_effect=TimeoutError("Haiku slow"))

    narrator_ran = False

    async def fake_narrator_call(*args, **kwargs):
        nonlocal narrator_ran
        narrator_ran = True
        from sidequest.agents.claude_client import ClaudeResponse
        return ClaudeResponse(text='{"narration": "ok"}', session_id="n", stop_reason="end_turn")

    sd.orchestrator._client = AsyncMock()
    sd.orchestrator._client.send_with_session = AsyncMock(side_effect=fake_narrator_call)

    await handler._execute_narration_turn(sd, "look around", _build_turn_context_for_test(sd))

    assert narrator_ran is True
```

- [ ] **Step 2: Run**

```bash
uv run pytest tests/server/test_session_handler_decomposer.py -v 2>&1 | tail -10
```

- [ ] **Step 3: Commit**

```bash
git add tests/server/test_session_handler_decomposer.py
git commit -m "test: integration — degraded decomposer does not block turn (group B task 14)"
```

---

## Task 15: Wiring test — confirm decomposer is reachable from production code path

**Files:**
- Modify: `tests/server/test_session_handler_decomposer.py`

**Context:** Per CLAUDE.md "Every Test Suite Needs a Wiring Test" — prove `LocalDM` is instantiated on session creation and callable during the real request lifecycle, not just reachable from the test's hand-built `_SessionData`.

This test uses the real session-open code path (e.g., `handle_session_open` or whatever REST/WS entry makes a new session) and confirms `sd.local_dm` exists and is the right type after.

- [ ] **Step 1: Identify session-open entry point**

```bash
grep -n "def handle_session_open\|def _open_session\|_SessionData(" /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b/sidequest/server/session_handler.py | head -10
```

- [ ] **Step 2: Append the wiring test**

```python
@pytest.mark.asyncio
async def test_session_open_initializes_local_dm(session_open_fixture):
    """After session open, _SessionData.local_dm is a live LocalDM instance."""
    from sidequest.agents.local_dm import LocalDM

    sd = await session_open_fixture()  # constructs via the real open path
    assert hasattr(sd, "local_dm")
    assert isinstance(sd.local_dm, LocalDM)
```

Provide a `session_open_fixture` that walks the real open path with a minimal genre/world (reuse existing server-test fixtures that already do this; they probably exist for smoke tests).

- [ ] **Step 3: Run**

```bash
uv run pytest tests/server/test_session_handler_decomposer.py::test_session_open_initializes_local_dm -v 2>&1 | tail -10
```

- [ ] **Step 4: Commit**

```bash
git add tests/server/test_session_handler_decomposer.py
git commit -m "test: wiring — LocalDM initialized on session open (group B task 15)"
```

---

## Task 16: Full server test suite + regression baseline + push + open PR

**Files:** none

**Context:** Close-out. Confirm the whole suite still passes, diff the test count against the Preflight 6 baseline, push, open PR.

- [ ] **Step 1: Full suite run**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b && just server-test 2>&1 | tee /tmp/group-b-final.txt | tail -10
```

Expected: all green. Compare pass counts:

```bash
grep -E "passed|failed" /tmp/group-b-baseline.txt | tail -1
grep -E "passed|failed" /tmp/group-b-final.txt | tail -1
```

Expected: final count = baseline + (new tests added by plan ≈ 35–40). Zero previously-passing tests now failing.

- [ ] **Step 2: Lint**

```bash
just server-lint 2>&1 | tail -10
```

Fix any new ruff findings before push.

- [ ] **Step 3: Push branch**

```bash
git push -u origin feat/local-dm-group-b
```

- [ ] **Step 4: Open PR (body via HEREDOC because `gh pr edit` lacks `read:org` scope)**

```bash
gh pr create --repo slabgorb/sidequest-server --base develop --title "Local DM Group B — Decomposer MVP (Haiku) + three subsystems + directive injection" --body "$(cat <<'EOF'
## Summary

Implements Story Group B from the Local DM decomposer design (spec `docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md`, §10 Story Group B).

- `DispatchPackage` pydantic contract in `sidequest/protocol/dispatch.py`
- `LocalDM` decomposer (Haiku-backed persistent session) in `sidequest/agents/local_dm.py`
- Three subsystems (`reflect_absence`, `distinctive_detail_hint`, `npc_agency`) + registry + bank executor in `sidequest/agents/subsystems/`
- `narrator_directives` prompt section injected at `AttentionZone.Fovea`
- `_execute_narration_turn` runs decomposer between sealed-letter completion and narrator call
- OTEL spans: `local_dm.decompose`, `local_dm.dispatch_bank`, `local_dm.subsystem`
- Unit + integration + wiring tests

## Non-goals (deferred to later groups)

- `LethalityVerdict` **producer** — Group C (contract is present; values stubbed)
- `VisibilityTag` **consumer** pipeline (Perception Rewriter, ProjectionFilter) — Group G
- Cross-player batched decompose — Group G alongside multiplayer
- Local fine-tune — Group E
- GM panel UI tab — Group C (when there's lethality content to visualize)

## Test plan

- [x] All existing server tests pass on `feat/local-dm-group-b` (see CI)
- [x] New: `tests/protocol/test_dispatch.py` — package roundtrip + validators
- [x] New: `tests/agents/test_local_dm.py` — referent resolution, absence, degraded paths, session lifecycle, spans
- [x] New: `tests/agents/subsystems/test_*.py` — each subsystem in isolation
- [x] New: `tests/agents/test_subsystem_registry.py` — registry + topo sort + idempotency + error handling
- [x] New: `tests/server/test_session_handler_decomposer.py` — full-turn integration (happy + absence + timeout + wiring)

## Spec-coverage checklist

- [x] §5 DispatchPackage contract (full shape including stubbed LethalityVerdict / VisibilityTag)
- [x] §6.1 happy path — pronoun resolved
- [x] §6.2 ambiguous pronoun — distinctive_detail_hint
- [x] §6.3 unresolvable referent — reflect_absence
- [x] §6.6 degraded path — timeout / parse failure / exception
- [x] §7 Phase A — Haiku persistent session
- [x] §8 coordination: topological sort, idempotency, partial failure handling

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 5: Commit any final touch-ups and verify PR URL**

```bash
git status
```

Record the PR URL in the session log.

---

## Post-Plan Self-Review Checklist

Before the first agent starts Task 1, the author (or next reviewer) walks through:

**Spec coverage** (spec §10 Story Group B bullets):

- [x] Define `DispatchPackage` types in `sidequest/protocol/` → Task 1
- [x] Build `LocalDM` class in `sidequest/agents/local_dm.py` → Tasks 2–3
- [x] Wire between `TurnPhase.InputCollection` completion and `TurnPhase.AgentExecution` → Task 10
- [x] Three initial subsystems (`reflect_absence` new, `distinctive_detail_hint` narrator directive, `npc_agency` wrap) → Tasks 4, 5, 6
- [x] Wire `narrator_instructions` into the existing `<game_state>` injection block via a new directives section → Task 9
- [x] OTEL spans on every dispatch → Task 11
- [x] GM panel tab — **deferred to Group C**, documented in the plan header (no mechanical content yet worth a UI surface)
- [x] Tests: unit (pronoun resolution) → Task 3; integration (happy + ambiguous + absence) → Tasks 12, 13; wiring → Task 15

**Known risks flagged in plan prose:**

- NPC registry API shape assumed — Task 6 prompts implementer to adapt fixture to real API.
- `build_narrator_prompt` may need async conversion — Task 9 Step 4 documents both options.
- `_SessionData` and `TurnContext` field-addition choices are documented; Task 10 adapts to whatever the real struct is.
- Subagent cwd drift — every task starts with `cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-b` to dodge the Group A gotcha.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-23-local-dm-group-b-decomposer-mvp.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration. Starts once Group A PRs #117 / #26 / #152 have merged on their respective bases.
2. **Inline Execution** — execute tasks in a single session using `executing-plans`, batch-with-checkpoints.

**Which approach?**
