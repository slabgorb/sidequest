# Anthropic SDK Migration: Cost Model + Tool-Use Surface

**Date:** 2026-05-15
**Author:** Architect (Keith Avery)
**Status:** Design — pending review
**Implementation target:** `feat/anthropic-sdk-migration` (single-branch Approach B)
**Supersedes (on landing):** ADR-001, ADR-039, ADR-058, ADR-028 (each gets a successor)
**Amends:** ADR-073
**Depends on (already shipped):** ADR-067 (unified narrator), ADR-098 (stateless narrator turns), ADR-073 (LLM-backend factory)

---

## Problem

Anthropic's June 15 2026 billing change moves `claude -p` (non-interactive Claude
Code CLI invocations) from the regular Claude.ai subscription pool into a separate
"programmatic credit" pool, billed at API list rates ($3/M input, $15/M output for
Sonnet 4.6), capped monthly per subscription tier (Pro $20, Max 5× $100, Max 20×
$200), non-rollover and non-fungible. SideQuest's `sidequest-server` exclusively
uses `claude -p` for narration (per ADR-001, enforced by the SDK-import grep test)
and is therefore directly affected.

At typical playgroup load (200-300 turns per 4-hour session, ~30k input / 2k
output per turn uncached), one weekly session at API list pricing burns
$24-36/week — pushing $96-144/month against a $200 cap with nothing left for dev
playtests, scenario tooling, or Sebastien's mechanical experiments. The current
architecture is economically unsustainable as of June 15 without intervention.

A secondary problem compounds the first: `claude -p` cannot call tools mid-
generation (memory: `project_claude_p_no_reactive_tools`). Every "structured"
output we extract from the narrator — dice rolls (ADR-074), state patches
(ADR-011/039), journal entries (ADR-100), disposition updates (ADR-020),
scenario advances (ADR-053) — comes via the ADR-039 JSON sidecar, a fenced-JSON
block parsed out of the narration text. The parser is fragile (~200 LOC of
malformed-JSON recovery), the narrator can lie about mechanical effects in prose
without the corresponding sidecar field, and ADR-031's "GM panel as lie
detector" is currently forensic (after-the-fact comparison) rather than
structural (provably no-such-action-occurred).

A third problem compounds further: the current narrator prompt is
prompt-stuffed — every turn carries PC sheets, NPC dispositions, lore RAG
dumps, monster manual entries, scenario state, and per-PC known-facts blocks,
regardless of whether the turn engages them. Most turns pay the full tax for
content unused. With caching unavailable to `claude -p`, this is paid in full
every turn.

## Goal

Migrate SideQuest's narrator path from `claude -p` subprocess to the Anthropic
SDK, capturing four compounding wins:

1. **Prompt caching** — 90% discount on cached input via `cache_control`, with
   stable prefix zones aligned to existing prompt structure
2. **Tool use** — JSON-Schema-validated, server-handled tool calls that replace
   the ADR-039 sidecar protocol with a structurally reliable, fully-typed
   surface
3. **Just-in-time retrieval** — narrator queries only the subsystems each turn
   needs, paying for content only when relevant
4. **Per-call model routing** — Haiku 4.5 for cheap auxiliary work, Sonnet 4.6
   for narration default, Opus 4.7 for declared-important moments, Batch API
   for between-scene work

Combined target: weighted-average per-turn cost of $0.05-0.07, compared to
~$0.12 for `claude -p` at June-16 API-billed rates. A typical 250-turn session
costs $12-18; a Max 20× cap of $200 covers ~12-14 sessions/month with margin.

Beyond cost, the migration is the structural enabler for three architectural
cleanups long deferred:

- **ADR-039 sidecar retirement** — every sidecar field has a typed-tool
  replacement; the parser is deleted
- **ADR-058 OTEL subprocess scraping retirement** — span emission moves from
  stderr-JSON parsing to native registry emit; the GM panel becomes a
  structural lie detector
- **ADR-028 perception rewriter retirement** — perception filtering moves from
  post-narration rewrite (2N model calls) to tool-result filter (N calls), with
  better quality because the narrator generates from a perception-correct view
  rather than redacting an omniscient one

## Non-goals

- Genre-pack-specific tools (e.g., `tea_and_murder`'s `query_clue_drawer`) —
  deferred to a post-migration follow-on epic after the registry pattern beds in
- Batch API integration for between-scene NPC simulation — flagged for future
  work, out of v1
- Migrating non-narrator paths off `ClaudeClient` — mood classifier, name gen,
  scratch jobs continue to use `ClaudeClient` (and may move to Ollama or the
  local fine-tuned model per ADR-073)
- Local fine-tuned model implementation — backlog stories 48-3 / 48-4 remain
  separate; this migration only narrows ADR-073's surface, doesn't subsume it
- UI changes for the GM panel to render the new OTEL surface — separate UI
  story after the spans land
- Changes to the multiplayer turn-coordination model (ADR-036), the
  shared/per-player state split (ADR-037), or the perception data model
  itself — only the *application point* of perception moves
- Removing the `claude -p` path entirely from the codebase — `ClaudeClient`
  remains for non-narrator paths

## Approach: single-branch big-bang (Approach B)

Three alternative migration shapes were considered:

- **Approach A — Sequential cutover:** Ship the backend swap + caching first
  as a complete change to `develop`; begin tool conversions afterward in
  batches. Lowest risk per change, but the prompt stays fat through the
  intermediate window (no slim wins until later phases land), and per-tool
  conversions on `develop` create awkward intermediate states the playgroup
  might see.
- **Approach B — Single big-bang on feature branch (selected):** Build the
  full migration on `feat/anthropic-sdk-migration`. `develop` stays on
  `claude -p` until merge. Single coordinated cutover when all 25 tools land
  and parity is validated.
- **Approach C — Strangler-fig coexistence:** SDK and CLI clients run side-by-
  side on `develop` via the existing factory; tools land one at a time. Each
  conversion is independently mergeable. Rejected: per-playtest mid-conversion
  states create variable game quality the playgroup will notice; the rebase
  burden across 25 incremental merges is heavier than one big merge from a
  feature branch.

Approach B was chosen because:
- `develop` is protected throughout migration — playgroup plays on the known-good
  path until the new path is fully validated
- Single squash-merge gives a clean revert path if a post-merge problem surfaces
- The "design coherence" wins of bundled landing (sidecar parser + perception
  rewriter + OTEL scraper all deleted in the same change) are achievable
- Feature-branch rebase against `develop` is manageable given Sprint 3 is in
  late cleanup mode

## Architecture overview

The migration touches three layers in `sidequest-server`; everything else stays
put.

```
┌──────────────────────────────────────────────────────────────────┐
│                     sidequest-server                              │
│                                                                   │
│  ┌──────────────────┐                                            │
│  │ agents/          │                                            │
│  │   orchestrator   │  build_narrator_prompt → SLIM PROMPT       │
│  │   narrator       │  (rules + recency + per-turn context)      │
│  │                  │                                            │
│  │   tool_registry  │← NEW: name→handler dispatcher             │
│  │                  │   wraps existing subsystem fns             │
│  │                  │                                            │
│  │   llm_factory ───┼→ ClaudeClient (kept; non-narrator only)    │
│  │                  │→ OllamaClient (kept; non-narrator only)    │
│  │                  │→ AnthropicSdkClient ← NEW: narrator path   │
│  │                  │     - tool_use protocol                    │
│  │                  │     - cache_control on prefix              │
│  │                  │     - model routing (Haiku/Sonnet/Opus)    │
│  │                  │     - streaming + tool round-trips         │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           │ (existing subsystems — UNCHANGED)                    │
│           ▼                                                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │ game/ (~70 mods) │  │ magic/           │  │ interior/      │ │
│  │ dice, lore_store,│  │ spell effects,   │  │ room state     │ │
│  │ monster_manual,  │  │ class powers     │  │                │ │
│  │ npc_pool,        │  └──────────────────┘  └────────────────┘ │
│  │ disposition,     │  ┌──────────────────┐  ┌────────────────┐ │
│  │ belief_state,    │  │ corpus/ (namegen)│  │ telemetry/     │ │
│  │ encounter,       │  └──────────────────┘  │ OTEL spans     │ │
│  │ gossip_engine    │                        │ ← new: tool    │ │
│  └──────────────────┘                        │ call spans     │ │
│                                              └────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

**What changes:**

- New `agents/anthropic_sdk_client.py` — implements both the existing narrow
  `LlmClient` protocol and a new richer `ToolingLlmClient` protocol that
  exposes tool_use round-trips, cache_control hints, and parallel tool dispatch
- New `agents/tool_registry.py` + `agents/tools/<tool_name>.py` (×26) — thin
  adapter layer wrapping existing subsystem functions
- `agents/orchestrator.py::build_narrator_prompt` — slimmed dramatically; most
  context blocks become tool definitions instead of inline content
- `telemetry/` gains a new span family for tool calls (replaces ADR-058
  subprocess JSON scraping)

**What stays untouched:**

- All ~70 modules in `game/`, `magic/`, `interior/`, `orbital/`, `corpus/` —
  existing subsystem functions are called by tool handlers; their internals are
  not modified
- The CLI generators (`cli/encountergen`, `cli/loadoutgen`, `cli/namegen`) —
  get tool wrappers, not rewrites
- WebSocket protocol layer (`protocol/`, `server/`, `handlers/`)
- The media daemon
- The UI
- Save/load and SQLite persistence
- ADR-036 (multiplayer turn coordination), ADR-037 (shared/per-player state
  split), ADR-067 (unified narrator), ADR-098 (stateless turns), ADR-100
  (journal pipeline) — survive unchanged

## `AnthropicSdkClient` and caching strategy

### Client interface

```python
# Narrow (existing LlmClient — text-in/text-out)
class LlmClient(Protocol):
    async def complete(self, prompt: str, system: str, *, model: str | None = None) -> str: ...

# Rich (new — narrator-only)
class ToolingLlmClient(LlmClient, Protocol):
    async def complete_with_tools(
        self,
        system_blocks: list[CacheableBlock],     # ordered; each has cache_control hint
        messages: list[Message],
        tools: list[ToolDefinition],
        *,
        model: str,
        max_iterations: int = 8,
        on_text_delta: Callable[[str], None] | None = None,
    ) -> ToolingResult: ...
```

The narrator orchestrator targets `complete_with_tools`. Auxiliary paths (mood
classifier, name gen, scratch jobs) target the narrow `complete`. `OllamaClient`
implements only the narrow protocol — type-system enforced separation prevents
narrator-on-Ollama paths.

`max_iterations=8` caps the tool-use loop. Typical turn uses 1-3 round-trips;
combat-heavy turns 4-6.

### Cache zones

```
┌──── system_blocks ────────────────────────────────────────────┐
│ Zone 1: SOUL.md + genre pack rules + tone-axis + verbosity    │
│         ~6-10k tokens, changes on pack edit only              │
│         cache_control: ephemeral  ← breakpoint 1              │
│                                                                │
│ Zone 2: Tool definitions (JSON schemas for all 26 tools)       │
│         ~2-3k tokens, changes on registry edit only           │
│         cache_control: ephemeral  ← breakpoint 2              │
│                                                                │
│ Zone 3: World snapshot — slim                                  │
│         ~1-2k tokens, changes on world-state patch             │
│         cache_control: ephemeral  ← breakpoint 3              │
└────────────────────────────────────────────────────────────────┘
┌──── messages (no cache markers; rolling content) ─────────────┐
│ Recent narration buffer (recency zone per ADR-098/49-1)        │
│ Current scene index (room/encounter pointer; no payloads)      │
│ Current PC action                                              │
└────────────────────────────────────────────────────────────────┘
```

Three of four available cache breakpoints used. Fourth reserved for a future
session-digest layer.

**Per-turn cost math (Sonnet 4.6 @ $3/M input, $0.30/M cached input, $15/M
output):**

| Component | Tokens | Cost |
|---|---|---|
| Zone 1+2+3 (cached, ~90% of turns) | 13,000 | $0.0039 |
| Rolling messages (uncached) | 6,000 | $0.0180 |
| Tool round-trips (1-3 typical) | ~2,000 in / ~1,500 out | $0.0285 |
| Final narration output | 2,000 | $0.0300 |
| **Total** | | **~$0.08/turn** |

This is the median turn. Quiet travel turns drop closer to $0.04; combat turns
rise to ~$0.10. Weighted average across typical session mix: **$0.05-0.07/turn**.

### Cache TTL

Default is 5 minutes; 1-hour beta is available and worth opting into for
playgroup-cadence sessions (4-hour sessions get one cache write per zone
instead of ~50). Spec calls for opting into 1-hour TTL beta at Phase A4.

### Model routing

| Call type | Default model | Override |
|---|---|---|
| Narration turn | Sonnet 4.6 | Opus 4.7 for Confrontation Def climaxes (ADR-033), tone-axis shifts (ADR-052), player-flagged "important" moments |
| Tool-handler reranker / classifier | Haiku 4.5 | n/a |
| Mood/intent classification | Haiku 4.5 | n/a |
| Name generation, scratch jobs | Haiku 4.5 or Ollama | n/a |
| Between-scene NPC simulation (future) | Sonnet 4.6 via Batch API (50% off) | n/a |

Configured in genre-pack YAML where pack-specific overrides apply. Default
ladder lives in `agents/model_routing.py`.

### Streaming + parallel tool use

The Anthropic API streams text deltas. When the model emits a tool_use block,
streaming pauses; the registry dispatches all parallel tool_use blocks
concurrently (asyncio.gather where category-safe); model resumes with new
stream after tool_result message. The `on_text_delta` callback wires through
the existing UI streaming path — no UI changes needed.

### Auth + retry

- `ANTHROPIC_API_KEY` env var; fail loud if missing on a narrator path
- Exponential backoff on 429 + 529 only; max 3 retries
- Permanent failure surfaces a structured error message into the narration
  stream ("the storyteller's connection was interrupted") rather than hanging
- `anthropic-ratelimit-*` response headers logged on every call; OTEL span
  when approaching cap

## Tool registry and adapter pattern

### Per-tool file shape (~30-60 LOC each)

```python
# agents/tools/lookup_monster.py
from sidequest.agents.tool_registry import tool, ToolContext, ToolResult
from sidequest.game.monster_manual import find_monster
from pydantic import BaseModel, Field

class LookupMonsterArgs(BaseModel):
    name: str = Field(..., description="Exact or common name; case-insensitive")
    include_stat_block: bool = Field(False, description="Returns full stat block; default returns only lore-safe surface")

@tool(
    name="lookup_monster",
    description=(
        "Fetch a monster manual entry by name. Use when a creature is engaged "
        "or referenced. Default omits stats — request include_stat_block=true "
        "only when actually resolving mechanics."
    ),
    category="read",
)
async def lookup_monster(args: LookupMonsterArgs, ctx: ToolContext) -> ToolResult:
    entry = find_monster(ctx.world_id, args.name)
    if entry is None:
        return ToolResult.not_found(f"No monster manual entry named {args.name!r}")
    payload = entry.to_lore_safe() if not args.include_stat_block else entry.to_full()
    return ToolResult.ok(payload)
```

Four things per adapter:

1. Pydantic args model — doubles as JSON Schema source via `.model_json_schema()`
2. `@tool` decorator — registers the adapter at import time with `name`,
   `description`, `category`
3. Async handler — pure function of `(args, ctx) → ToolResult`
4. Calls into the existing subsystem — no new logic

### `ToolContext` — injected runtime, model never sees

```python
@dataclass(frozen=True)
class ToolContext:
    world_id: str
    session_id: str
    perspective_pc: CharacterId | None  # set for narrator; None for tests
    turn_number: int
    store: SqliteStore                  # game state read/write
    otel_span: trace.Span               # parent span for child tool spans
    perception_filter: PerceptionFilter # ADR-028 successor — see below
```

### `ToolResult` — three states

```python
class ToolResult:
    @classmethod
    def ok(cls, payload: dict | BaseModel) -> "ToolResult": ...
    @classmethod
    def not_found(cls, message: str) -> "ToolResult": ...   # model may retry
    @classmethod
    def error(cls, message: str, recoverable: bool = True) -> "ToolResult": ...
```

`error(recoverable=True)` → tool_result with `is_error: true`; model self-
corrects. `error(recoverable=False)` → registry aborts turn cleanly.

### Categories — `read` / `write` / `generate`

| Category | Examples | Transaction? | Span name | Cache impl |
|---|---|---|---|---|
| `read` | `lookup_monster`, `query_lore`, `query_npc` | No | `tool.read.{name}` | Cacheable per-turn |
| `write` | `apply_damage`, `update_npc_disposition` | Yes (SQLite) | `tool.write.{name}` | Invalidates downstream |
| `generate` | `roll_dice`, `generate_loadout`, `generate_name` | No | `tool.gen.{name}` | Per-call seeded |

### Registration — explicit, no magic

`agents/tools/__init__.py` imports each tool module by name. `@tool`'s only
side effect is appending to a module-level list in `tool_registry`. Tests can
build registries from fresh module namespaces without polluting global state.

### Dispatch flow

```
model emits tool_use block(s)
   │
   ▼
registry.dispatch(blocks, ctx)
   │
   ├─→ start OTEL span tool.{cat}.{name}
   │
   ├─→ validate args via Pydantic
   │
   ├─→ open transaction if cat == "write"
   │
   ├─→ await handler(args, ctx)
   │
   ├─→ apply ctx.perception_filter (read/generate)
   │
   ├─→ end span, commit/rollback txn
   │
   └─→ return tool_result message
```

Parallel tool_use blocks in a single model response dispatched concurrently;
write tools serialize per-session.

### Flat namespace decision

26 tools, flat namespace, one purpose per tool — no mega-tools with `action`
discriminators. Empirically the model picks tools better when each has one
purpose; flat names map 1:1 to OTEL span names; ADR-039 sidecar retirement is
tracked per-tool rather than per-namespace.

## Tool catalog (v1)

26 tools across 9 subsystems. All use existing subsystem functions; the adapter
is the only new code per subsystem.

### Resolution & combat (4)

| Tool | Cat | Source | Retires from prompt |
|---|---|---|---|
| `roll_dice` | gen | `game/dice.py::roll` + `generate_dice_seed` | ADR-039 sidecar `dice_roll`; ADR-074 WS round-trip block |
| `apply_damage` | write | `game/character.py` HP + `game/combatant.py` | Sidecar `patches[]` HP; injected combatant-HP block |
| `apply_status` | write | `game/status.py` | Sidecar `patches[]` status; active-status list |
| `update_resource_pool` | write | `game/resource_pool.py` (mana, edge, composure per ADR-078) | Resource block per ADR-078 |

### Character & inventory (1 consolidated)

| Tool | Cat | Source | Retires |
|---|---|---|---|
| `query_character` | read | `game/character.py`, `game/builder.py` | Full PC sheet block (~2-5k tokens stuffed every turn); `include=[stats, inventory, status, backstory]` for field selection |

### NPCs (3)

| Tool | Cat | Source | Retires |
|---|---|---|---|
| `query_npc` | read | `game/npc_pool.py` + `game/disposition.py` | Active-NPC disposition block (perception-filtered) |
| `list_npcs_in_scene` | read | `game/npc_pool.py` scene-scoped | Injected "NPCs present" enumeration |
| `update_npc_disposition` | write | `game/disposition.py` axis mutation | Sidecar `patches[]` disposition |

### Belief / journal / gossip (3)

| Tool | Cat | Source | Retires |
|---|---|---|---|
| `query_known_facts` | read | `game/belief_state.py` (ADR-100) | Per-PC known-facts block (biggest single token win) |
| `commit_known_fact` | write | `game/belief_state.py` + `game/event_log.py` | Sidecar `journal_entries[]`; ADR-100 footnote |
| `query_gossip` | read | `game/gossip_engine.py` | Injected NPC gossip block |

### Lore & reference (2)

| Tool | Cat | Source | Retires |
|---|---|---|---|
| `query_lore` | read | `game/lore_store.py::query_by_*` (already a query API) | Pre-injected RAG dump (ADR-048) |
| `lookup_monster` | read | `game/monster_manual.py` | ADR-059 server-side pre-injection |

### Scene & scenario (3)

| Tool | Cat | Source | Retires |
|---|---|---|---|
| `query_scene_state` | read | `game/scenario_state.py` + `interior/` | Room + active-beat + tension block |
| `query_scenario_clues` | read | `game/scenario_state.py` (ADR-053 clue graph) | Injected clue-graph state |
| `advance_scene_clue` | write | `game/scenario_state.py` transition | Sidecar `scenario_advances[]` |

### Encounter & combat structure (2)

| Tool | Cat | Source | Retires |
|---|---|---|---|
| `query_encounter` | read | `game/encounter.py` + `game/beat_filter.py` | Initiative + current-beat block |
| `advance_encounter_beat` | write | `game/encounter.py` beat transition | Sidecar `encounter_advances[]` |

### Trope & confrontation (2)

| Tool | Cat | Source | Retires |
|---|---|---|---|
| `tick_tropes` | write | `game/taunt_tick.py` + `game/taunt.py` (ADR-018) | Active-tropes block + sidecar trope-tick |
| `advance_confrontation` | write | `game/encounter.py` confrontation track (ADR-033) | Confrontation block + sidecar |

### Magic (2)

| Tool | Cat | Source | Retires |
|---|---|---|---|
| `query_magic_state` | read | `magic/` package | Active-spells + mana-pool block |
| `apply_spell_effect` | write | `magic/` effect resolver | Sidecar `magic_effects[]` |

### Generators (3)

| Tool | Cat | Source | Retires |
|---|---|---|---|
| `generate_name` | gen | `corpus/` Markov + ADR-091 culture-corpus | Pre-generated NPC name lists |
| `generate_loadout` | gen | `cli/loadoutgen` | Injected "available loadouts" block |
| `generate_encounter` | gen | `cli/encountergen` | Injected encounter seeds |

### Escape hatch (1)

| Tool | Cat | Source | Retires |
|---|---|---|---|
| `apply_world_patch` | write | `game/delta.py` + `game/shared_world_delta.py` (ADR-011) | Sidecar `patches[]` for anything not yet typed |

### ADR-039 sidecar coverage map (definition-of-done check)

Phase C's done condition is this table fully ✅:

| Sidecar field | Retired by | v1 |
|---|---|---|
| `dice_roll` | `roll_dice` | ✅ |
| `patches[]` HP / damage | `apply_damage` | ✅ |
| `patches[]` status | `apply_status` | ✅ |
| `patches[]` resource pools | `update_resource_pool` | ✅ |
| `patches[]` disposition | `update_npc_disposition` | ✅ |
| `patches[]` (other) | `apply_world_patch` | ✅ (escape hatch) |
| `journal_entries[]` | `commit_known_fact` | ✅ |
| `scenario_advances[]` | `advance_scene_clue` | ✅ |
| `encounter_advances[]` | `advance_encounter_beat` | ✅ |
| `magic_effects[]` | `apply_spell_effect` | ✅ |
| Trope ticks | `tick_tropes` | ✅ |
| Confrontation advances | `advance_confrontation` | ✅ |

## Slim prompt target

After Phase C lands, `build_narrator_prompt` produces:

| Zone | Content | Tokens |
|---|---|---|
| Zone 1 (cached) | SOUL.md + genre pack rules + verbosity + tone-axis spec + lethality policy | 6,000-10,000 |
| Zone 2 (cached) | JSON Schema + descriptions for all 26 tools + per-category usage guidance | 2,000-3,000 |
| Zone 3 (cached) | World snapshot (slim): name, region, calendar/season, major flags, active scenario pointer, tone-axis snapshot | 1,000-2,000 |
| Messages (uncached) | Recency narration buffer + scene-index pointers (entity names only, no payloads) + per-turn action | 5,000-10,000 |
| **Total** | | **~14-25k, median ~20k** |

vs. current `claude -p` prompt at ~25-50k tokens (median ~30k), all uncached.

**Cache-hit fraction:** ~60% after migration (vs. ~29% current), because the
stable prefix is a larger fraction of total.

**Scene-index pointer block** is the key new primitive: tells the narrator what
*exists* (PC names, NPC names by name, room ID, encounter ID, scenario clue
IDs, active trope names) without giving content. The narrator queries content
via tools when needed.

### Cost breakdown by turn type

| Turn type | Frequency | Cost |
|---|---|---|
| Quiet travel / social (0-1 tool calls) | ~40% | $0.03-0.05 |
| Standard scene work (2-3 tool calls) | ~45% | $0.05-0.08 |
| Combat / mechanical (4-6 tool calls) | ~15% | $0.08-0.12 |
| **Weighted average** | | **$0.05-0.07** |

A 250-turn / 4-hour session: **$12-18**.

## OTEL / observability

### Span hierarchy

```
narration.turn (root)
├── attrs: world_id, session_id, turn_number, acting_pc, model_chosen,
│          cache_read_tokens, cache_write_tokens, total_input_tokens,
│          total_output_tokens, total_cost_usd, tool_call_count
│
├── llm.request.1
│   ├── attrs: model, input_tokens, output_tokens, cached_input_tokens,
│   │          stop_reason, ratelimit_remaining
│   └── (children: tool spans when stop_reason == "tool_use")
│
├── tool.read.query_npc
│   └── attrs: tool_name, tool_category, duration_ms, result_status,
│              result_size_bytes, perspective_pc, tool.npc.name,
│              tool.npc.perception_filtered
│
├── llm.request.2 (model continues after tool results)
│
├── tool.write.apply_damage
│   ├── attrs: ..., tool.damage.target_pc, tool.damage.hp_delta,
│   │          tool.damage.source, tool.cache_invalidates
│   └── db.transaction (child)
│       └── attrs: txn_id, rows_affected, duration_ms
│
└── llm.request.3 (final narration)
    └── attrs: stop_reason: "end_turn"
```

### Standard attributes (every tool span)

```
tool.name              "query_character"
tool.category          "read" | "write" | "generate"
tool.result_status     "ok" | "not_found" | "error_recoverable" | "error_fatal"
tool.result_size_bytes 1247
tool.duration_ms       4.2
tool.perspective_pc    "alex_pc_id" | null
tool.cache_invalidates ["character.alex"]   # write tools only
```

Per-tool typed attributes namespaced as `tool.<short_name>.*`.

### ADR-031 watcher event mapping

| ADR-031 event | New home |
|---|---|
| Intent classification | Attribute on `llm.request.1` |
| Agent routing | Eliminated (ADR-067 — unified narrator) |
| State patches | `tool.write.*` spans |
| Inventory mutations | `tool.write.update_resource_pool` |
| NPC registry events | `tool.write.update_npc_disposition` + `tool.read.query_npc` |
| Trope engine ticks | `tool.write.tick_tropes` |
| Encounter beat selections | `tool.write.advance_encounter_beat` |
| Magic activations | `tool.write.apply_spell_effect` |

### Structural lie detection

Three classes of verification become possible:

1. **Mechanical assertion without action.** Narration mentions damage but no
   `tool.write.apply_damage` span → flagged.
2. **State described without query.** Narration describes NPC mood but no
   `tool.read.query_npc` span → either improvisation or hallucination.
3. **Multiplayer perception violation.** Narration includes content perception
   filter should have hidden → flagged against the span's `perspective_pc`.

ADR-058's subprocess JSON scraping is deleted; the path becomes native
registry emission. ADR-031's principle survives, mechanism replaced.

## Perception filtering at the tool layer

### Replaces ADR-028 post-pass rewriter

**Current (ADR-028):**

| Step | What | Cost |
|---|---|---|
| 1 | Narrator generates omniscient narration | 1× call |
| 2 | Per-PC rewriter pass | +N× rewrite calls |
| **Total** | | **N+1 calls per multiplayer turn** |

**New:**

| Step | What | Cost |
|---|---|---|
| 1 | For each acting PC: narrator generates with `perspective_pc` set; tool results perception-filtered server-side | N× calls |

Per-tool filter rules:

| Tool | Filter |
|---|---|
| `query_npc` | Disposition filtered to what `perspective_pc` has observed; charm/deception applied |
| `query_known_facts` | Returns only `perspective_pc`'s facts (ADR-100) |
| `query_lore` | Filtered to lore PC has access to; classified info hidden |
| `query_scene_state` | Filtered to PC line-of-sight/audibility |
| `lookup_monster` | "Lore-safe" surface default; `include_stat_block=true` perception-gated |
| `query_encounter` | Foe HP coarsened ("unwounded/wounded/bloodied/staggering") |
| `query_magic_state` | PC's own exact; others' visible-effects only |
| `query_gossip` | Filtered to what PC has heard / could overhear |
| `query_scenario_clues` | Filtered to clues this PC has discovered |
| `query_character` | Self exact; party coarsened HP; non-party hidden |

Write tools: mutations objective (HP decrements regardless of perception); the
*result_status* may include `observed: false, narration_hint: "..."` to signal
the model the action happened off-camera.

### Multiplayer cost scaling

N PCs in a scene:
- Current ADR-028: N+1 model calls per turn
- New: N model calls per turn

Cache reuse across PCs in same turn: high — Zone 1+2+3 identical for all N
narrators; only the variable tool-result content differs. 4-PC turns get
cheaper *per PC* than single-PC turns.

### Doctrine preservation

CLAUDE.md collaborative-visibility doctrine (peer action text visible during
submit-and-wait per ADR-036) is preserved unchanged. Sealed-visibility (PvP
hidden submission) remains unimplemented and reserved.

The new architecture supports sealed-visibility trivially when implemented:
route a PC's narration only to that client and don't broadcast. No rewriter
gymnastics needed.

## Testing strategy

### Surface 1 — Per-tool unit tests (~75-125 tests)

Each adapter, `(args, ctx) → ToolResult`. Pattern:

- Happy path
- Perception-filter behavior (read tools)
- Not-found / error path
- Args validation
- For writes: state-mutation + transaction rollback on error

### Surface 2 — Registry / dispatch integration

- Parallel dispatch
- Write transaction rollback on error
- Perception filter applied to result
- Recoverable error returns to model
- Fatal error aborts turn cleanly

### Surface 3 — End-to-end wiring tests (the CLAUDE.md mandate)

Uses `FakeAnthropicSdkClient` scripted per test. Three scenarios:

- Combat turn (read + read + write + narration)
- Social/investigation turn (multiple reads, no writes)
- Quiet travel turn (zero tools)

Plus one negative wiring test (broken handler → clean failure, no half-written
state).

### Surface 4 — Narration parity (Phase A / Phase B validation)

Run scene-harness fixtures (Wave 1 / Wave 2 from #221) against both backends,
assert structural properties (length range, mechanical events fired, no
contradictions, no uncalled subsystems).

### Surface 5 — Playtest scenarios

`scenarios/*.yaml` re-run on feature branch, compared to develop baselines.
One live playgroup session as final acceptance.

### `FakeAnthropicSdkClient`

One mock, used by every non-API test. No real API calls in any test. CI runs
offline.

### Per-conversion test pattern (during Phase C)

1. Before-state regression test (fixture exercises sidecar field)
2. Conversion landing (new adapter passes unit + wiring tests)
3. After-state acceptance (same fixture, tool span emitted, sidecar field gone)
4. Cleanup (before-state regression deleted in commit that deletes sidecar
   handler)

## Migration sequencing

`feat/anthropic-sdk-migration`, Approach B. 41 stories across 5 phases,
~111-137 story points, ~3-4 sprints at current velocity.

### Phase A — Foundation (4 stories, 18 pts)

| # | Story | Pts |
|---|---|---|
| A1 | Draft + commit migration ADR (supersedes 001, 039, 058, 028; amends 073) | 3 |
| A2 | `AnthropicSdkClient` + `ToolingLlmClient` + `FakeAnthropicSdkClient` | 8 |
| A3 | Cache zone structure + `cache_control` wiring + cost telemetry rollup | 5 |
| A4 | Opt into 1-hour cache TTL beta; `model_routing.py` | 2 |

### Phase B — Registry (3 stories, 18 pts)

| # | Story | Pts |
|---|---|---|
| B1 | `tool_registry.py` + `@tool` + `ToolContext` + `ToolResult` + dispatch | 8 |
| B2 | `PerceptionFilter` primitive (registry hook; no-op default) | 5 |
| B3 | OTEL span emission + cost-rollup attributes | 5 |

### Phase C — Tool conversions (26 stories, ~52-78 pts)

Risk-ordered:

| Block | Tools | # |
|---|---|---|
| C1 simplest | `roll_dice` | 1 |
| C2 first writes | `apply_damage`, `apply_status`, `update_resource_pool` | 3 |
| C3 character | `query_character` | 1 |
| C4 NPCs | `query_npc`, `list_npcs_in_scene`, `update_npc_disposition` | 3 |
| C5 belief/journal | `query_known_facts`, `commit_known_fact`, `query_gossip` | 3 |
| C6 reference | `query_lore`, `lookup_monster` | 2 |
| C7 scene/scenario | `query_scene_state`, `query_scenario_clues`, `advance_scene_clue` | 3 |
| C8 encounter | `query_encounter`, `advance_encounter_beat` | 2 |
| C9 trope/confrontation | `tick_tropes`, `advance_confrontation` | 2 |
| C10 magic | `query_magic_state`, `apply_spell_effect` | 2 |
| C11 generators | `generate_name`, `generate_loadout`, `generate_encounter` | 3 |
| C12 escape hatch | `apply_world_patch` | 1 |

Each story: adapter file + unit tests + prompt block removal + wiring test
update + before/after fixture parity + coverage map update.

### Phase D — Cleanup (5 stories, 16 pts)

| # | Story | Pts |
|---|---|---|
| D1 | Delete sidecar parser + recovery + dispatch | 3 |
| D2 | Delete ADR-028 post-pass rewriter | 3 |
| D3 | Delete ADR-058 subprocess JSON scraping (narrator path) | 2 |
| D4 | Final slim of `build_narrator_prompt` | 5 |
| D5 | Write successor ADRs | 3 |

### Phase E — Merge (3 stories, 7 pts)

| # | Story | Pts |
|---|---|---|
| E1 | Run all `scenarios/*.yaml`; capture baselines | 2 |
| E2 | Live playgroup session on feature branch | 3 |
| E3 | Code review, squash-merge to `develop`, deploy | 2 |

### Branch hygiene

- Weekly rebase against `develop` (Fridays)
- No `git stash` per [[feedback_commit_dont_stash]]
- No squash-inside-branch per [[feedback_stacked_branch_orphan_drop]]
- `just check-all` on every push

### Rollback plan

1. **Per-tool regression** — revert that conversion's commits; re-add prompt
   block + sidecar field; story re-opened
2. **Mid-migration full revert** — abandon branch; `develop` untouched; restart
   with lessons learned
3. **Post-merge revert** — revert the squash-merge commit on `develop`

`SIDEQUEST_LLM_BACKEND` env var is **not** a post-merge rollback mechanism —
once Phase D deletes the sidecar parser and prompt instructions, toggling back
to `claude` would produce broken narration. The merge is a one-way door.

### Sprint tracking

This migration is its own epic in Sprint 4 (next sprint after Sprint 3 closes).
Phase mapping to epic stories matches Phases A-E above. Stories tagged with
phase letter in `sprint/sprint-N.yaml`.

## ADR consequences

| ADR | Disposition | Successor |
|---|---|---|
| 001 — Claude CLI Only | superseded | "Anthropic SDK as Narrator Backend" |
| 039 — JSON sidecar | superseded | "Tool-Use Protocol for Structured Output" |
| 058 — Claude subprocess OTEL passthrough | superseded | "Native OTEL via Tool Registry" |
| 028 — Perception rewriter | superseded | "Perception Filtering at the Tool Layer" |
| 073 — Local fine-tuned model architecture | amended (narrowed) | (no successor — header amendment only) |

ADRs surviving unchanged:
- 009 (attention-aware zones), 011 (world state JSON patches), 031 (game
  watcher principle), 036 (multiplayer turn coordination), 037 (shared/per-
  player state split), 048 (lore RAG), 053 (scenario clue graph), 059 (monster
  manual server-side), 067 (unified narrator), 074 (dice WS protocol — at
  transport layer), 090 (OTEL dashboard infrastructure), 098 (stateless
  narrator), 100 (journal pipeline)

ADR-013 (lazy JSON extraction) becomes obsolete with sidecar retirement — flag
in DRIFT.md or absorb into ADR-039 successor.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| API key compromise / cost runaway | Spend telemetry on every turn (`narration.turn.cost_usd`); alert at $X/hour; Anthropic console rate limits |
| Narration quality regression on SDK | Surface 4 parity tests + Surface 5 playtest scenarios + live playgroup session E2; per-tool conversion has before/after fixture comparison |
| 1-hour cache TTL beta is unreliable | Fallback to 5-minute TTL is automatic (just cost; not correctness); telemetry includes `cache_read_tokens` / `cache_write_tokens` to detect regression |
| Tool selection regression (model picks wrong tool) | Per-tool descriptions are tuned in Phase C with playtest feedback; failing parity tests catch this; can pin specific model versions if drift |
| Mid-migration playgroup session feels weird | Phase B+C+D land before any playgroup session sees the branch; playgroup plays on `develop` until Phase E2 |
| Branch drift from `develop` | Weekly rebase; Sprint 3 is in late cleanup so drift is small |
| `apply_world_patch` becomes a long-tail dependency | Deprecation criterion: zero `tool.write.apply_world_patch` spans in 10 consecutive playtest scenarios before Phase D |
| Type-system separation between `LlmClient` and `ToolingLlmClient` proves wrong (e.g., a non-narrator path wants caching) | Caching can be added to the narrow protocol later if needed; no down-side to starting strict |

## Open questions deferred to writing-plans

- Exact `ToolDefinition` and `CacheableBlock` dataclass shapes
- Per-tool JSON Schema details
- Per-adapter perception-filter test fixtures
- Whether trope/confrontation get explicit `query_tropes` / `query_confrontation`
  read companions (currently subsumed by `tick_tropes`/`advance_confrontation`
  read paths)
- Specific ADR numbering for the four successor ADRs
- Genre-pack-specific tool catalogs (post-migration follow-on; not v1)
- Batch API integration for between-scene work (post-migration follow-on; not v1)

## Success criteria

1. All 25 tools registered and exercised by playtest scenarios
2. ADR-039 sidecar coverage map fully ✅
3. `agents/claude_stream_parser.py` sidecar paths deleted
4. ADR-028 perception rewriter deleted
5. ADR-058 subprocess JSON scraping (narrator path) deleted
6. `build_narrator_prompt` produces median ~20k-token output
7. Per-turn cost telemetry shows weighted average $0.05-0.07 across a full
   playtest session
8. Live playgroup session on the feature branch produces narration Keith
   approves as "still SideQuest"
9. Squash-merge to `develop` lands cleanly with all `just check-all` checks
   green
10. Four successor ADRs written and committed alongside the merge
