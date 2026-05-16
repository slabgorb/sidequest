# Anthropic SDK Migration — Phase C: Tool Conversions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the 26 v1 tools from the design spec, one per task, in risk order. Each conversion (a) lands a new adapter under `sidequest/agents/tools/<name>.py`, (b) removes the corresponding pre-injected content block from `build_narrator_prompt`, (c) adds the per-tool rule to `NarratorPerceptionFilter`, (d) ticks one row in the ADR-039 sidecar coverage map, (e) keeps before/after parity on at least one scene-harness fixture.

**Architecture:** Each tool is a `~30-60 LOC` adapter — Pydantic args model + `@tool`-decorated async handler that calls existing subsystem functions. No new domain logic; only adaptation. Risk order from spec §Migration sequencing: `roll_dice` (simplest, validates the entire stack) → first writes → character → NPCs → belief → reference → scene → encounter → trope → magic → generators → escape hatch.

**Tech Stack:** Same as Phases A+B.

**Scope:** Phase C only — 26 stories (C1-C12 blocks), ~52-78 pts. Phases A and B must be merged to the feature branch before this plan starts. Phase D (cleanup) deletes the sidecar parser and ADR-028 rewriter only after this phase's coverage map is fully ticked.

**Branch:** `feat/anthropic-sdk-migration` (same branch as Phase A+B) in `sidequest-server/`.

---

## File Structure

**Created (per-tool, 26 of each):**
- `sidequest-server/sidequest/agents/tools/<tool_name>.py`
- `sidequest-server/tests/agents/tools/test_<tool_name>.py`

**Created (shared):**
- `sidequest-server/sidequest/agents/narrator_perception_filter.py` — concrete `PerceptionFilter` with per-tool rules (Task 0)
- `sidequest-server/tests/agents/tools/__init__.py`
- `sidequest-server/tests/agents/test_narrator_perception_filter.py`
- `sidequest-server/tests/agents/test_sidecar_coverage_map.py` — meta-test asserting all sidecar fields have a tool successor

**Modified per tool:**
- `sidequest-server/sidequest/agents/tools/__init__.py` — add one import line
- `sidequest-server/sidequest/agents/orchestrator.py::build_narrator_prompt` — remove the corresponding pre-injected content block (and the helpers that built it, if unused elsewhere)
- `sidequest-server/sidequest/agents/narrator_perception_filter.py` — add the per-tool rule
- `docs/adr/039-narrator-structured-output.md` — annotate the migrated field with `migrated-to: tool:<name>` (frontmatter trailer; Phase D writes the successor ADR)

**Modified once:**
- `sidequest-server/sidequest/agents/__init__.py` — export `NarratorPerceptionFilter`

---

## Self-Review (pre-execution)

Spec coverage: the per-tool table below maps 1:1 to the spec's §Tool catalog (v1). Sidecar coverage-map test (Task 28) is the structural enforcement of completion.

Type consistency: every adapter uses `(args: SomeArgs, ctx: ToolContext) -> ToolResult`. `SomeArgs` is a Pydantic `BaseModel` per tool. The `@tool` decorator (Phase B) is the only registration mechanism.

Placeholder scan: every per-tool task lists the specific args fields, the specific subsystem function to call, and the specific prompt block to remove.

---

## Task 0 — `NarratorPerceptionFilter` skeleton

The concrete filter for narrator paths. Starts with all rules as no-op (delegates to the result unchanged); each subsequent tool-conversion task fills in its rule.

**Files:**
- Create: `sidequest-server/sidequest/agents/narrator_perception_filter.py`
- Create: `sidequest-server/tests/agents/test_narrator_perception_filter.py`

- [ ] **Step 0.1: Write the failing test**

```python
"""Tests for NarratorPerceptionFilter — dispatches per-tool rules."""

from __future__ import annotations

from sidequest.agents.narrator_perception_filter import NarratorPerceptionFilter
from sidequest.agents.tool_registry import ToolCategory, ToolResult


def test_filter_passes_through_unknown_tool() -> None:
    f = NarratorPerceptionFilter()
    r = ToolResult.ok({"x": 1})
    out = f.filter_result(
        tool_name="brand_new_tool",
        category=ToolCategory.READ,
        result=r,
        perspective_pc="alex",
    )
    assert out.payload == {"x": 1}


def test_filter_passes_through_write_results() -> None:
    f = NarratorPerceptionFilter()
    r = ToolResult.ok({"applied": True})
    out = f.filter_result(
        tool_name="apply_damage",
        category=ToolCategory.WRITE,
        result=r,
        perspective_pc="alex",
    )
    assert out.payload == {"applied": True}
```

- [ ] **Step 0.2: Implement**

```python
"""NarratorPerceptionFilter — concrete filter with per-tool rules.

Each per-tool rule is a function `(payload, perspective_pc) -> payload`.
Phase C tool conversions register their rule via the _RULES table.
Write tools are unfiltered (mutations are objective).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sidequest.agents.tool_registry import ToolCategory, ToolResult, ToolResultStatus

_RuleFn = Callable[[Any, str | None], Any]
_RULES: dict[str, _RuleFn] = {}


def register_rule(tool_name: str, fn: _RuleFn) -> None:
    if tool_name in _RULES:
        raise ValueError(f"Perception rule for {tool_name!r} already registered")
    _RULES[tool_name] = fn


class NarratorPerceptionFilter:
    def filter_result(
        self,
        *,
        tool_name: str,
        category: ToolCategory,
        result: ToolResult,
        perspective_pc: str | None,
    ) -> ToolResult:
        if category is ToolCategory.WRITE:
            return result
        if result.status is not ToolResultStatus.OK:
            return result
        rule = _RULES.get(tool_name)
        if rule is None:
            return result
        new_payload = rule(result.payload, perspective_pc)
        return ToolResult.ok(new_payload)
```

- [ ] **Step 0.3: Run + commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_narrator_perception_filter.py -v
uv run ruff check sidequest/agents/narrator_perception_filter.py tests/agents/test_narrator_perception_filter.py
uv run pyright sidequest/agents/narrator_perception_filter.py
git add sidequest/agents/narrator_perception_filter.py tests/agents/test_narrator_perception_filter.py
git commit -m "feat(agents): add NarratorPerceptionFilter with per-tool rule table"
```

- [ ] **Step 0.4: Create the tools tests package marker**

```bash
mkdir -p /Users/slabgorb/Projects/oq-1/sidequest-server/tests/agents/tools
```

Create `tests/agents/tools/__init__.py`:
```python
"""Per-tool adapter tests."""
```

---

## Task 1 — Tool conversion template (the recipe)

Every per-tool task follows this exact pattern. Per-tool tasks (Tasks 2-27) list only the deltas: tool name, args fields, subsystem function, prompt block to remove, perception rule, OTEL attrs.

### Template steps (do these for each tool)

- [ ] **T.1: Identify the prompt block to remove**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
grep -n "<the block marker from the per-tool task>" sidequest/agents/orchestrator.py sidequest/agents/narrator_prompts/*.py 2>/dev/null
```

- [ ] **T.2: Write the failing adapter test**

Create `tests/agents/tools/test_<name>.py` with:
- happy path (returns `ToolResult.ok` with the expected payload)
- not-found path (where applicable)
- args validation rejection (where the args have non-trivial constraints)
- perception filter applied (for `read` category tools)
- For `write` tools: state mutation visible to a subsequent read + transaction rollback on exception in the subsystem call

Test fixtures use `tests/agents/conftest.py` helpers where they exist (look at `tests/agents/conftest.py` first; reuse don't reinvent).

- [ ] **T.3: Implement the adapter**

Create `sidequest/agents/tools/<name>.py`:
```python
"""Tool: <name>. Adapter for <subsystem>."""

from __future__ import annotations

from pydantic import BaseModel, Field

from sidequest.<subsystem>.<module> import <fn>
from sidequest.agents.tool_registry import (
    ToolCategory,
    ToolContext,
    ToolResult,
    tool,
)


class <Name>Args(BaseModel):
    # field declarations from the per-tool task
    pass


@tool(
    name="<name>",
    description="<one-paragraph description from the per-tool task>",
    category=ToolCategory.<READ|WRITE|GENERATE>,
)
async def <name>(args: <Name>Args, ctx: ToolContext) -> ToolResult:
    # 1. Set per-tool OTEL attributes via ctx.otel_span.set_attribute(...)
    # 2. Call the existing subsystem function
    # 3. Return ToolResult.ok(payload) | not_found(...) | error(...)
    ...
```

- [ ] **T.4: Add the perception rule (read/generate tools only)**

Append to `sidequest/agents/narrator_perception_filter.py`:
```python
def _filter_<name>(payload: Any, perspective_pc: str | None) -> Any:
    # implementation per the per-tool task's "Perception rule" line
    ...

register_rule("<name>", _filter_<name>)
```

Plus a test in `tests/agents/test_narrator_perception_filter.py` that exercises the rule.

- [ ] **T.5: Import the adapter in the tools barrel**

Add to `sidequest/agents/tools/__init__.py`:
```python
from sidequest.agents.tools import <name>  # noqa: F401
```

- [ ] **T.6: Remove the prompt block**

Edit `sidequest/agents/orchestrator.py::build_narrator_prompt` (and any helpers it calls). Delete the lines that build the pre-injected block (per T.1). If the helpers become unused, delete them too. Run existing orchestrator tests to confirm no regression on non-narrator paths.

- [ ] **T.7: Before/after scene-harness fixture**

Add one scene-harness fixture in `scenarios/sidecar_parity/<name>_v1.yaml` (or extend an existing fixture if it already exercises the field). Run twice:

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
SIDEQUEST_LLM_BACKEND=claude uv run python -m sidequest.cli.scene_harness scenarios/sidecar_parity/<name>_v1.yaml --record baseline
SIDEQUEST_LLM_BACKEND=anthropic_sdk ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY uv run python -m sidequest.cli.scene_harness scenarios/sidecar_parity/<name>_v1.yaml --record migrated
```

Assert structural parity via the harness's diff tool: same mechanical events fire, no missing state transitions, narration length within tolerance. (The scene-harness tooling already exists from ADR-092 / sprint 50 — confirm the `--record` and diff subcommands or use what's there.)

- [ ] **T.8: Tick the sidecar coverage map**

Edit `tests/agents/test_sidecar_coverage_map.py` (created in Task 28; for the first per-tool conversion you'll create that test file first). Set the `<sidecar_field>` row to `migrated_to="<tool_name>"`.

- [ ] **T.9: Lint + type-check + commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/agents/tools/<name>.py tests/agents/tools/test_<name>.py
uv run pyright sidequest/agents/tools/<name>.py
uv run pytest tests/agents/tools/test_<name>.py tests/agents/test_narrator_perception_filter.py -v
git add sidequest/agents/tools/<name>.py tests/agents/tools/test_<name>.py sidequest/agents/tools/__init__.py sidequest/agents/narrator_perception_filter.py sidequest/agents/orchestrator.py tests/agents/test_sidecar_coverage_map.py tests/agents/test_narrator_perception_filter.py scenarios/sidecar_parity/<name>_v1.yaml
git commit -m "feat(tools): convert <name> — <one-line summary>

<short body referencing which sidecar field / prompt block this retires
and which subsystem it adapts>"
```

---

## Per-tool tasks

Each table row below is a Phase C story. Block ordering matches spec §Migration sequencing risk order. Within a block, do tools in the order listed.

### Block C1 — Simplest (1 tool)

#### Task 2: `roll_dice`

| Field | Value |
|---|---|
| Category | `generate` |
| Subsystem | `sidequest/game/dice.py` |
| Function | `roll(notation, seed=None)` |
| Args | `notation: str` (e.g. `"d20"`, `"3d6+2"`), `seed: int | None = None`, `reason: str = ""` |
| Description | "Roll dice for a mechanical resolution. Use whenever a check, save, or damage roll is needed. `notation` accepts standard dice notation; `reason` is a one-line label for the OTEL span." |
| Prompt block to remove | None (current dice path is a WS round-trip per ADR-074, not an injected block — the conversion just routes calls through the tool path) |
| Perception rule | none (results are objective rolls) |
| OTEL attrs | `tool.dice.notation`, `tool.dice.value`, `tool.dice.seed` |
| Sidecar field | `dice_roll` |
| ADR | ADR-074 (dice WS protocol — preserved at transport layer; this only affects how narrator *requests* a roll) |

**Implementation notes:** The handler returns `ToolResult.ok({"value": total, "rolls": [individual], "notation": notation, "seed": seed_used})`. The existing `roll()` function in `game/dice.py` already returns a structured result — just wrap it.

**Tests:**
- d20 returns 1-20
- 3d6+2 returns 5-20
- Invalid notation returns `ToolResult.error` (recoverable)
- OTEL span carries `tool.dice.notation` and `tool.dice.value`

### Block C2 — First writes (3 tools)

#### Task 3: `apply_damage`

| Field | Value |
|---|---|
| Category | `write` |
| Subsystem | `sidequest/game/character.py` (HP) + `sidequest/game/combatant.py` |
| Function | Locate the existing damage-application function; likely `apply_damage(character_id, amount, source=...)` or similar. Use grep: `grep -n "def apply_damage\|hp -= \|take_damage" sidequest/game/character.py sidequest/game/combatant.py` |
| Args | `target: str` (character or combatant id), `amount: int = Field(..., ge=0)`, `damage_type: str = "untyped"`, `source: str = ""` |
| Description | "Apply HP damage to a character or combatant. Use after a roll has determined the damage amount. `damage_type` is genre-flavored (slashing/fire/psychic/etc.); `source` is a one-line cause description." |
| Prompt block to remove | The injected combatant-HP block in `build_narrator_prompt` — search for "HP:" or "combatant_block" |
| Perception rule | none (write) |
| OTEL attrs | `tool.damage.target`, `tool.damage.hp_delta`, `tool.damage.damage_type`, `tool.damage.source`, `tool.damage.target_hp_after` |
| Sidecar field | `patches[]` HP entries |
| ADR | ADR-039 |

**Tests:**
- damage reduces HP by amount
- amount=0 is valid (no-op) and emits the span anyway
- Unknown target returns `not_found`
- Two parallel damage tools against same session run sequentially (already covered by Phase B test; add a smoke test here)

#### Task 4: `apply_status`

| Field | Value |
|---|---|
| Category | `write` |
| Subsystem | `sidequest/game/status.py` |
| Function | `apply_status(target, status_name, duration_rounds=None, source="")` (verify exact name with grep) |
| Args | `target: str`, `status: str`, `duration_rounds: int | None = None`, `source: str = ""` |
| Description | "Apply a status condition (prone, dazed, charmed, etc.) to a character or combatant. `duration_rounds=None` means until cleared by another effect." |
| Prompt block to remove | Active-status enumeration in `build_narrator_prompt` |
| Perception rule | none (write) |
| OTEL attrs | `tool.status.target`, `tool.status.name`, `tool.status.duration_rounds` |
| Sidecar field | `patches[]` status entries |

**Tests:** status appears on subsequent `query_character`; duration tick is governed by existing status engine (untouched here).

#### Task 5: `update_resource_pool`

| Field | Value |
|---|---|
| Category | `write` |
| Subsystem | `sidequest/game/resource_pool.py` (ADR-078 edge/composure + magic mana) |
| Function | `adjust(target, pool_name, delta)` (verify; likely already exists per ADR-078 implementation) |
| Args | `target: str`, `pool: str` (e.g. `"mana"`, `"edge"`, `"composure"`), `delta: int`, `source: str = ""` |
| Description | "Adjust a resource pool by signed delta. Negative spends, positive restores. `pool` names are genre-defined." |
| Prompt block to remove | Per-character resource block in `build_narrator_prompt` |
| Perception rule | none (write) |
| OTEL attrs | `tool.resource.target`, `tool.resource.pool`, `tool.resource.delta`, `tool.resource.value_after` |
| Sidecar field | `patches[]` resource_pool entries |

### Block C3 — Character (1 tool)

#### Task 6: `query_character`

| Field | Value |
|---|---|
| Category | `read` |
| Subsystem | `sidequest/game/character.py`, `sidequest/game/builder.py` |
| Function | Locate the existing serializer — `Character.to_dict()` or similar |
| Args | `character_id: str`, `include: list[Literal["stats","inventory","status","backstory","resources"]] = Field(default_factory=lambda: ["stats","status"])` |
| Description | "Fetch a character sheet by id. `include` selects sections to return — request only what the current turn needs to keep the response slim." |
| Prompt block to remove | Full PC sheet block (largest single token win — likely ~2-5k tokens per turn) |
| Perception rule | "Self exact; party-member HP coarsened to wounded/bloodied/staggering; non-party PCs hidden." Implementation: if `perspective_pc != character_id` and character is in party → coarsen `hp_current` to a band; if not in party → return `not_found`. |
| OTEL attrs | `tool.character.id`, `tool.character.include`, `tool.character.perception_coarsened` (bool) |
| Sidecar field | none (this is purely retrieval) |

**Tests:**
- Self returns full HP
- Other party PC returns coarsened HP
- Non-party PC returns not_found
- `include=["stats"]` omits inventory etc.

### Block C4 — NPCs (3 tools)

#### Task 7: `query_npc`

| Field | Value |
|---|---|
| Category | `read` |
| Subsystem | `sidequest/game/npc_pool.py`, `sidequest/game/disposition.py` |
| Function | `find_npc(world_id, npc_id)` + `get_disposition(npc_id, perspective_pc)` (verify names) |
| Args | `npc_id: str`, `include_disposition: bool = True`, `include_backstory: bool = False` |
| Description | "Fetch an NPC entry by id. Disposition is per-perspective: what THIS PC has observed of the NPC, not the omniscient view." |
| Prompt block to remove | Active-NPC disposition block |
| Perception rule | "Disposition filtered to observed-by-pc only; charm/deception layered on top of objective disposition." Use existing `disposition.observed_view(npc_id, perspective_pc)` if it exists; otherwise stub a redaction. |
| OTEL attrs | `tool.npc.id`, `tool.npc.name`, `tool.npc.perception_coarsened` |
| Sidecar field | none |

#### Task 8: `list_npcs_in_scene`

| Field | Value |
|---|---|
| Category | `read` |
| Subsystem | `sidequest/game/npc_pool.py` (scene-scoped query) + `sidequest/interior/` (room scope) |
| Function | `npcs_in_scene(world_id, scene_id)` |
| Args | `scene_id: str | None = None` (None = current scene from `ctx.store`) |
| Description | "List NPCs present in the current (or specified) scene. Returns ids + display names only — call `query_npc` to fetch details." |
| Prompt block to remove | Injected "NPCs present" enumeration |
| Perception rule | Filter to NPCs the perspective_pc can perceive (line-of-sight, audibility — reuse interior/perception logic if present) |
| OTEL attrs | `tool.npcs.count` |
| Sidecar field | none |

#### Task 9: `update_npc_disposition`

| Field | Value |
|---|---|
| Category | `write` |
| Subsystem | `sidequest/game/disposition.py` |
| Function | `adjust_axis(npc_id, axis, delta, perspective_pc=None)` |
| Args | `npc_id: str`, `axis: str`, `delta: float`, `perspective_pc: str | None = None`, `reason: str = ""` |
| Description | "Adjust an NPC's disposition along a named axis (trust, fear, respect, etc.). Per-PC dispositions adjust the PC-specific view; omitting perspective_pc adjusts the global view." |
| Prompt block to remove | The disposition-snapshot block |
| Perception rule | none (write) |
| OTEL attrs | `tool.disposition.npc_id`, `tool.disposition.axis`, `tool.disposition.delta`, `tool.disposition.perspective_pc` |
| Sidecar field | `patches[]` disposition |

### Block C5 — Belief / journal / gossip (3 tools)

#### Task 10: `query_known_facts`

| Field | Value |
|---|---|
| Category | `read` |
| Subsystem | `sidequest/game/belief_state.py` (ADR-100) |
| Function | `known_facts(perspective_pc, topic=None)` |
| Args | `topic: str | None = None`, `confidence_min: Literal["suspected","known","certain"] = "suspected"` |
| Description | "Return facts the perspective PC has registered as known/suspected/certain. Filter by topic substring or confidence floor." |
| Prompt block to remove | Per-PC known-facts block (biggest non-character token win) |
| Perception rule | "Only perspective_pc's facts — never another PC's." Implementation: ignore the model's request if `perspective_pc` is None; otherwise scope to that PC. |
| OTEL attrs | `tool.belief.fact_count`, `tool.belief.topic` |
| Sidecar field | none (this is read) |
| ADR | ADR-100 |

#### Task 11: `commit_known_fact`

| Field | Value |
|---|---|
| Category | `write` |
| Subsystem | `sidequest/game/belief_state.py`, `sidequest/game/event_log.py` |
| Function | `commit_fact(perspective_pc, text, confidence, source)` |
| Args | `text: str`, `confidence: Literal["suspected","known","certain"] = "known"`, `source: str = "narrator"`, `topic_tags: list[str] = Field(default_factory=list)` |
| Description | "Commit a fact to the perspective PC's belief state. Use after a discovery, conversation, or clue resolution. Sets confidence per the ADR-100 enum." |
| Prompt block to remove | none (already not in prompt — only the journal sidecar) |
| Perception rule | none (write) |
| OTEL attrs | `tool.belief.fact_id`, `tool.belief.confidence`, `tool.belief.topic_tags` |
| Sidecar field | `journal_entries[]` |
| ADR | ADR-100 |

#### Task 12: `query_gossip`

| Field | Value |
|---|---|
| Category | `read` |
| Subsystem | `sidequest/game/gossip_engine.py` |
| Function | `gossip_for(perspective_pc, scene_id=None, since_turn=None)` |
| Args | `scene_id: str | None = None`, `since_turn: int | None = None` |
| Description | "Fetch gossip the perspective PC could plausibly have heard. Filter by scene or recency." |
| Prompt block to remove | Injected NPC-gossip block |
| Perception rule | Filter to gossip propagated within audibility / social reach of `perspective_pc` |
| OTEL attrs | `tool.gossip.item_count` |
| Sidecar field | none |

### Block C6 — Lore & reference (2 tools)

#### Task 13: `query_lore`

| Field | Value |
|---|---|
| Category | `read` |
| Subsystem | `sidequest/game/lore_store.py` (ADR-048) |
| Function | `query_by_topic(topic, k=5)` and/or `query_by_embedding(query, k=5)` — the lore_store already exposes a query API |
| Args | `topic_or_query: str`, `k: int = Field(5, ge=1, le=20)` |
| Description | "RAG query against the world lore store. Returns top-k matching lore entries with embedding similarity." |
| Prompt block to remove | Pre-injected RAG dump in `build_narrator_prompt` |
| Perception rule | "Filter to lore the perspective PC could access. Hide lore tagged classified/secret unless the PC has the secret-tag." Implementation: filter result rows by tag intersection with PC's known-tags set. |
| OTEL attrs | `tool.lore.k`, `tool.lore.hit_count`, `tool.lore.top_score` |
| Sidecar field | none |
| ADR | ADR-048 |

#### Task 14: `lookup_monster`

| Field | Value |
|---|---|
| Category | `read` |
| Subsystem | `sidequest/game/monster_manual.py` |
| Function | `find_monster(world_id, name)` |
| Args | `name: str`, `include_stat_block: bool = False` |
| Description | "Fetch a monster manual entry by name. Default returns the lore-safe surface (description, behavior cues); request `include_stat_block=true` only when actually resolving mechanics." |
| Prompt block to remove | ADR-059 server-side pre-injection — the orchestrator was injecting the full bestiary into the prompt; this tool retires that |
| Perception rule | `include_stat_block=true` is perception-gated: only return stats if the PC's recognize-check has succeeded or the GM has flagged the monster as known. For Phase C v1: hard-gate the stat block on a `monster_known(perspective_pc, monster_id)` lookup; default to lore-safe if not. |
| OTEL attrs | `tool.monster.name`, `tool.monster.stat_block_included` |
| Sidecar field | none |
| ADR | ADR-059 |

### Block C7 — Scene & scenario (3 tools)

#### Task 15: `query_scene_state`

| Field | Value |
|---|---|
| Category | `read` |
| Subsystem | `sidequest/game/scenario_state.py` + `sidequest/interior/` |
| Function | `current_scene(session_id)` returning room + active-beat + tension snapshot |
| Args | none required; optional `include: list[str] = ["room","beat","tension"]` |
| Description | "Fetch the current scene's room id, active beat (encounter or social), and tension level. Use to ground narration in the current setting." |
| Prompt block to remove | Room + active-beat + tension block |
| Perception rule | Coarsen tension axis to PC's perception of it (e.g. PC who's panicking may see different tension level); for v1 hide nothing — return raw. |
| OTEL attrs | `tool.scene.room_id`, `tool.scene.beat`, `tool.scene.tension` |
| Sidecar field | none |

#### Task 16: `query_scenario_clues`

| Field | Value |
|---|---|
| Category | `read` |
| Subsystem | `sidequest/game/scenario_state.py` (ADR-053 clue graph) |
| Function | `clue_graph_state(world_id, perspective_pc)` |
| Args | `include_undiscovered_titles: bool = False` |
| Description | "Return the scenario clue graph state from the perspective PC's view: discovered clues + their links. Set `include_undiscovered_titles=true` only for GM debug — narrator should default to false." |
| Prompt block to remove | Injected clue-graph state |
| Perception rule | "Hide clues this PC hasn't discovered; only their titles (and only when `include_undiscovered_titles=true`)." |
| OTEL attrs | `tool.clue_graph.discovered_count`, `tool.clue_graph.undiscovered_count` |
| Sidecar field | none |
| ADR | ADR-053 |

#### Task 17: `advance_scene_clue`

| Field | Value |
|---|---|
| Category | `write` |
| Subsystem | `sidequest/game/scenario_state.py` transition |
| Function | `advance_clue(world_id, clue_id, perspective_pc, evidence_text=None)` |
| Args | `clue_id: str`, `evidence_text: str = ""` |
| Description | "Mark a clue as advanced (discovered/connected) by the perspective PC. Records evidence text into the clue graph." |
| Prompt block to remove | (already not in prompt — sidecar-only) |
| Perception rule | none (write) |
| OTEL attrs | `tool.clue.id`, `tool.clue.transition`, `tool.clue.perspective_pc` |
| Sidecar field | `scenario_advances[]` |
| ADR | ADR-053 |

### Block C8 — Encounter & combat structure (2 tools)

#### Task 18: `query_encounter`

| Field | Value |
|---|---|
| Category | `read` |
| Subsystem | `sidequest/game/encounter.py`, `sidequest/game/beat_filter.py` |
| Function | `current_encounter(session_id)` returning initiative + current beat |
| Args | none |
| Description | "Fetch initiative order and current encounter beat. Returns combatant ids + names; call `query_character` / `lookup_monster` for details." |
| Prompt block to remove | Initiative + current-beat block |
| Perception rule | "Foe HP coarsened to unwounded/wounded/bloodied/staggering." Implementation: scrub `current_hp` to band labels. |
| OTEL attrs | `tool.encounter.id`, `tool.encounter.beat`, `tool.encounter.combatant_count` |
| Sidecar field | none |

#### Task 19: `advance_encounter_beat`

| Field | Value |
|---|---|
| Category | `write` |
| Subsystem | `sidequest/game/encounter.py` |
| Function | `advance_beat(encounter_id, to_beat=None)` |
| Args | `to_beat: str | None = None` (None = auto-advance via existing beat-selection logic) |
| Description | "Transition the encounter to its next beat (or a specific beat). Beat names are encounter-template-defined." |
| Prompt block to remove | (sidecar-only) |
| Perception rule | none (write) |
| OTEL attrs | `tool.encounter.beat_from`, `tool.encounter.beat_to` |
| Sidecar field | `encounter_advances[]` |

### Block C9 — Trope & confrontation (2 tools)

#### Task 20: `tick_tropes`

| Field | Value |
|---|---|
| Category | `write` |
| Subsystem | `sidequest/game/taunt_tick.py`, `sidequest/game/taunt.py` (ADR-018) |
| Function | `tick(session_id, narration_text)` |
| Args | `narration_text: str` (the text the narrator is about to say; tropes engage on keyword/situation matches in this text) |
| Description | "Tick the trope engine against pending narration. Run once per turn AFTER the narrative text is settled but BEFORE end_turn — gives the trope engine a chance to register escalation." |
| Prompt block to remove | Active-tropes block |
| Perception rule | none (write) |
| OTEL attrs | `tool.tropes.engaged_count`, `tool.tropes.engaged_names` |
| Sidecar field | trope-tick |
| ADR | ADR-018 |

#### Task 21: `advance_confrontation`

| Field | Value |
|---|---|
| Category | `write` |
| Subsystem | `sidequest/game/encounter.py` confrontation track (ADR-033) |
| Function | `advance_confrontation(confrontation_id, axis, delta, reason="")` |
| Args | `confrontation_id: str`, `axis: str`, `delta: int`, `reason: str = ""` |
| Description | "Advance a Confrontation Def axis by a delta. Use during structured confrontations (combat, chase, trial, poker, debate) to record progress toward the resolution threshold." |
| Prompt block to remove | Confrontation block |
| Perception rule | none (write) |
| OTEL attrs | `tool.confrontation.id`, `tool.confrontation.axis`, `tool.confrontation.delta`, `tool.confrontation.value_after` |
| Sidecar field | confrontation advances |
| ADR | ADR-033 |

### Block C10 — Magic (2 tools)

#### Task 22: `query_magic_state`

| Field | Value |
|---|---|
| Category | `read` |
| Subsystem | `sidequest/magic/` package |
| Function | `magic_state_for(character_id)` returning active spells + mana pool |
| Args | `character_id: str` |
| Description | "Fetch the character's active spells, prepared spells (if applicable), and mana pool state." |
| Prompt block to remove | Active-spells + mana-pool block |
| Perception rule | "Self exact; others' visible effects only (active spell auras observable to onlookers); mana pool hidden for non-self." |
| OTEL attrs | `tool.magic.character_id`, `tool.magic.active_spell_count`, `tool.magic.mana_remaining` |
| Sidecar field | none |

#### Task 23: `apply_spell_effect`

| Field | Value |
|---|---|
| Category | `write` |
| Subsystem | `sidequest/magic/` effect resolver |
| Function | locate via `grep -n "def resolve\|def apply_effect" sidequest/magic/` |
| Args | `spell_id: str`, `caster: str`, `targets: list[str]`, `cost: int = 0`, `overrides: dict[str, Any] = Field(default_factory=dict)` |
| Description | "Apply a spell's effect to its targets via the magic resolver. `overrides` permits per-cast tuning the model expresses (e.g., maximizing range)." |
| Prompt block to remove | (sidecar-only) |
| Perception rule | none (write) |
| OTEL attrs | `tool.spell.id`, `tool.spell.caster`, `tool.spell.target_count`, `tool.spell.cost` |
| Sidecar field | `magic_effects[]` |

### Block C11 — Generators (3 tools)

#### Task 24: `generate_name`

| Field | Value |
|---|---|
| Category | `generate` |
| Subsystem | `sidequest/corpus/` Markov + ADR-091 culture-corpus |
| Function | `generate(culture, kind="given", count=1)` (locate exact name) |
| Args | `culture: str`, `kind: Literal["given","family","place","tavern","ship"] = "given"`, `count: int = Field(1, ge=1, le=10)` |
| Description | "Generate one or more names from the named culture's corpus via the Markov chain. Cultures are genre-pack-defined." |
| Prompt block to remove | Pre-generated NPC name lists |
| Perception rule | none |
| OTEL attrs | `tool.namegen.culture`, `tool.namegen.kind`, `tool.namegen.count` |
| Sidecar field | none |
| ADR | ADR-091 |

#### Task 25: `generate_loadout`

| Field | Value |
|---|---|
| Category | `generate` |
| Subsystem | `sidequest/cli/loadoutgen` |
| Function | Locate the entry function the CLI uses internally |
| Args | `archetype: str`, `tier: int = Field(1, ge=1, le=5)`, `genre: str | None = None` |
| Description | "Generate an equipment loadout for an archetype + tier. Used for NPC outfitting and player-facing gear options." |
| Prompt block to remove | Injected "available loadouts" block |
| Perception rule | none |
| OTEL attrs | `tool.loadout.archetype`, `tool.loadout.tier`, `tool.loadout.item_count` |
| Sidecar field | none |

#### Task 26: `generate_encounter`

| Field | Value |
|---|---|
| Category | `generate` |
| Subsystem | `sidequest/cli/encountergen` |
| Function | Locate the entry function the CLI uses internally |
| Args | `genre: str`, `difficulty: int = Field(2, ge=1, le=5)`, `terrain: str | None = None`, `theme: str | None = None` |
| Description | "Generate an encounter seed (combatant types + difficulty rating + suggested terrain features). Use when an encounter needs to be invented mid-session." |
| Prompt block to remove | Injected encounter seeds |
| Perception rule | none |
| OTEL attrs | `tool.encgen.genre`, `tool.encgen.difficulty`, `tool.encgen.combatant_count` |
| Sidecar field | none |

### Block C12 — Escape hatch (1 tool)

#### Task 27: `apply_world_patch`

| Field | Value |
|---|---|
| Category | `write` |
| Subsystem | `sidequest/game/delta.py`, `sidequest/game/shared_world_delta.py` (ADR-011) |
| Function | `apply_patch(world_id, json_patch)` |
| Args | `path: str` (JSON Pointer e.g. `/world/towns/montmartre/weather`), `value: Any`, `reason: str` |
| Description | "Apply a JSON-patch-style mutation to world state. **Escape hatch only** — prefer a typed tool when one exists. Heavily logged; deprecation criterion is zero spans across 10 consecutive playtests." |
| Prompt block to remove | Sidecar `patches[]` for un-typed mutations |
| Perception rule | none (write) |
| OTEL attrs | `tool.world_patch.path`, `tool.world_patch.reason`, `tool.world_patch.path_kind` (extract first segment for cardinality control) |
| Sidecar field | `patches[]` (other) |
| ADR | ADR-011 |

**Important:** This tool is the deprecation lever. Phase D includes a check that `apply_world_patch` invocation count is zero across the parity fixtures before sidecar deletion can proceed.

---

## Task 28 — Sidecar coverage map (meta-test)

**Files:**
- Create: `sidequest-server/tests/agents/test_sidecar_coverage_map.py`

Single test file enforcing the spec's §ADR-039 sidecar coverage map. Updates across the per-tool tasks; this task creates the initial table and the assertion structure.

- [ ] **Step 28.1: Create the coverage map test**

```python
"""Sidecar coverage map — enforces Phase C definition-of-done.

Each row maps a former sidecar field to its successor tool. Phase D
cannot proceed until every row has a successor.
"""

from __future__ import annotations

import pytest

# Each entry: sidecar_field -> successor tool name (or None if not yet migrated).
COVERAGE_MAP: dict[str, str | None] = {
    "dice_roll": None,
    "patches_hp": None,
    "patches_status": None,
    "patches_resource_pool": None,
    "patches_disposition": None,
    "patches_other": None,
    "journal_entries": None,
    "scenario_advances": None,
    "encounter_advances": None,
    "magic_effects": None,
    "trope_tick": None,
    "confrontation_advances": None,
}


def test_phase_c_complete() -> None:
    """Phase D gate — must pass before deleting the sidecar parser."""
    unmigrated = [k for k, v in COVERAGE_MAP.items() if v is None]
    assert not unmigrated, (
        f"Sidecar fields without tool successors: {unmigrated!r}. "
        "Phase D cannot proceed."
    )
```

- [ ] **Step 28.2: Commit (skip the gate test for now)**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add tests/agents/test_sidecar_coverage_map.py
git commit -m "test(agents): add sidecar coverage map meta-test

Phase D gate. Each per-tool conversion updates the map entry for its
field; Phase D's cleanup tasks cannot proceed until every entry has a
non-None successor."
```

Mark `test_phase_c_complete` as `xfail` or skip via `pytest.skip` initially — flip to a hard assert after the last per-tool conversion (Task 27) is committed and the map is fully populated. Practical approach: each per-tool task's commit also updates this map; the test goes from xfail to passing on the last update.

---

## Task 29 — Phase C acceptance: full sweep + push

- [ ] **Step 29.1: Confirm coverage map full**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_sidecar_coverage_map.py -v
```

Expected: pass with no xfail / skip — every sidecar field has a successor.

- [ ] **Step 29.2: Confirm all 26 tools registered**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run python -c "
from sidequest.agents.tools import *  # noqa: F401,F403 — triggers registrations
from sidequest.agents import default_registry
names = default_registry.list_names()
print(f'{len(names)} tools:', names)
assert len(names) == 26, f'expected 26 tools, got {len(names)}'
"
```

Expected: `26 tools: [..., 'apply_damage', 'apply_spell_effect', ..., 'update_resource_pool']`.

- [ ] **Step 29.3: Run full suite**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest -v
```

- [ ] **Step 29.4: Lint / format / type sweep**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

- [ ] **Step 29.5: Run all scene-harness parity fixtures**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run python -m sidequest.cli.scene_harness scenarios/sidecar_parity/ --diff
```

Expected: every fixture's `baseline` vs `migrated` diff is structurally clean (mechanical events match; narration prose may differ — that's allowed within tolerance).

- [ ] **Step 29.6: Orchestrator gate**

```bash
cd /Users/slabgorb/Projects/oq-1/
just check-all
```

- [ ] **Step 29.7: Push**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git push origin feat/anthropic-sdk-migration
```

---

## Phase C completion check

- [ ] **All 26 tools registered.** (Task 29.2)
- [ ] **Sidecar coverage map full.** (Task 29.1)
- [ ] **Scene-harness fixtures pass diff parity.** (Task 29.5)
- [ ] **Narrator path still on `claude -p` in production.** The slim prompt was modified, but the narrator's actual LLM client is still `ClaudeClient` until Phase E. The orchestrator changes in Phase C remove pre-injected blocks; this is *prep* for the SDK path, not a switchover.

> **Important:** Because Phase C removed pre-injected blocks from `build_narrator_prompt`, the `claude -p` narrator path is **degraded** during Phase C — the prompt is slim but `claude -p` can't call tools to recover the content. **Phase D is required before any playgroup session sees the feature branch.** Spec §Approach assumed this.

---

## What's next

Phase D plan: `2026-05-15-anthropic-sdk-migration-phase-d-cleanup.md` — delete sidecar parser, ADR-028 rewriter, ADR-058 scraping; final prompt slim; write successor ADRs.
