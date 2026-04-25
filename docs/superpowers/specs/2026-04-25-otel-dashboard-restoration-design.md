# OTEL Dashboard Restoration After Python Port

**Date:** 2026-04-25
**Author:** Architect (consulting with Keith Avery)
**Status:** Approved design — ready for implementation plan
**Related:** ADR-031 (Game Watcher — Semantic Telemetry), ADR-058 (Claude subprocess OTEL passthrough), ADR-082 (Port `sidequest-api` from Rust back to Python)
**Resulting ADR:** ADR-089 (to be drafted with this spec)

---

## 1. Problem

The OTEL dashboard at `/ws/watcher` and the React `Dashboard/` panes have degraded considerably since the Rust → Python port (ADR-082). The CLAUDE.md "OTEL Observability Principle" — *"every backend fix that touches a subsystem MUST add OTEL watcher events so the GM panel can verify the fix is working"* — is no longer enforced. The GM panel's "lie detector" property, on which Sebastien-the-mechanics-first-player and Keith-the-builder both depend, is broken.

A forensic audit of `sidequest-server/` produced four root-cause findings:

### 1.1 `just otel` recipe is broken outright

`justfile:189` invokes `scripts/playtest.py --dashboard-only --dashboard-port {port}`. That file does not exist. Story 21-1 split it into `playtest_dashboard.py`, `playtest_otlp.py`, and `playtest_messages.py`; the `just` recipe was never updated. Running `just otel` errors immediately:

```
can't open file '.../scripts/playtest.py': [Errno 2] No such file or directory
error: Recipe `otel` failed
```

The dashboard cannot be opened from the documented entry point.

### 1.2 The dashboard contract is mostly stubs

`sidequest-ui/src/types/watcher.ts` declares 11 `WatcherEventType` values. Production-code emission count:

| Event type | Sites | Status |
|---|---|---|
| `agent_span_close` | auto | ✅ Every closed OTEL span fans out via `WatcherSpanProcessor` |
| `agent_span_open` | 1 | ⚠️ Only the handshake "hello" frame |
| `state_transition` | ~30 | ✅ Healthy — `session_handler.py` + `narration_apply.py` |
| `turn_complete` | **1** | ⚠️ Single emission; `TurnCompleteFields` mostly under-populated |
| `lore_retrieval` | 1 | ⚠️ One site |
| `prompt_assembled` | 1 | ⚠️ One site |
| `game_state_snapshot` | 2 | ⚠️ Two sites |
| `validation_warning` | **0** | ❌ Not emitted anywhere |
| `subsystem_exercise_summary` | **0** | ❌ Not emitted — kills the Subsystems tab |
| `coverage_gap` | **0** | ❌ Not emitted |
| `json_extraction_result` | **0** | ❌ Not emitted — extraction-tier lie detector is gone |

The four `0` rows are the ADR-031 Layer-3 narrative-validation pipeline. It was never ported. There is no `TurnRecord`, no validator queue, no checks.

### 1.3 ~80% of `spans.py` is dead constants

`sidequest/telemetry/spans.py` defines roughly 80 `SPAN_*` constants (port-named after Rust source files). Of those, only ~14 helpers have any production call site. Specifically dead — constants exist, **no emission anywhere in production code**:

- `SPAN_TURN` itself — the root turn span never opens. Every other span is therefore orphaned in the trace; the Timing tab cannot group spans by turn, the Subsystems tab cannot say "subsystems exercised this turn."
- All trope spans (`SPAN_TROPE_TICK`, `_ACTIVATE`, `_RESOLVE`, `_TICK_PER`, `_ROOM_TICK`, `_CROSS_SESSION`, `_EVALUATE_TRIGGERS`)
- All persistence spans (`_SAVE`, `_LOAD`, `_DELETE`)
- All chargen spans
- Most NPC/disposition/creature spans
- All state-patch spans (`SPAN_APPLY_WORLD_PATCH`, `SPAN_QUEST_UPDATE`, `SPAN_BUILD_PROTOCOL_DELTA`, `SPAN_COMPUTE_DELTA`)
- Inventory extraction, narrator/barrier, music, RAG, scenario, monster manual, reminders, pregen, catch-up, script tool, world materialization, merchant, content resolve, continuity validation, compose
- Most `SPAN_TURN_*` sub-spans
- Most `SPAN_ORCHESTRATOR_*` injection spans

The Python catalog was *transcribed* from Rust, but the dispatch-path *emission sites* were never re-implanted into the Python dispatch tree. Large parts of the catalog are aspirational.

### 1.4 The translator is impoverished

`WatcherSpanProcessor.on_end` (`server/watcher.py:64-86`) flattens **every** closed OTEL span to `event_type: "agent_span_close"` with `fields: {name, duration_ms, ...attrs}`. There is no semantic-translation step that maps span families to typed events. In Rust, domain code emitted both spans and typed `tracing::info!`/`warn!` events; in Python, `publish_event(...)` exists but is rarely invoked from inside the dispatch path. The dashboard's typed-event tabs receive a flat firehose they cannot classify.

### 1.5 Architectural framing

The Python port copied the **vocabulary** (span name catalog) and the **transport** (`WatcherSpanProcessor`, hub, `/ws/watcher`), but not the **emission discipline** or **Layer-3 validator**. ADR-031 specifies a three-layer model — Transport, Agent, Narrative. The Python server has Layer 1, a fragmentary Layer 2, and no Layer 3 at all.

---

## 2. Decision: Faithful Port of ADR-031, Full Parity

Restore the OTEL dashboard to the three-layer semantic-telemetry contract specified in ADR-031, faithfully ported to Python. After this work:

- Every subsystem the GM panel was designed to surface emits live signals.
- Every `WatcherEventType` declared in `watcher.ts` carries data.
- The catalog stops being aspirational.
- The translator owns typed-event routing for every span family with semantic content.
- The validator pipeline (ADR-031 Layer 3) exists as Python `asyncio` infrastructure.

### 2.1 Three deliberate departures from the Rust ADR

1. **`TurnRecord` shape.** Rust cloned two full `GameSnapshot`s per turn. Python stores `snapshot_before_hash + snapshot_after + StateDelta`. Same validation power, no double-clone cost. Rationale: Python copy semantics + GIL make full-snapshot doubling expensive; the hash supports "did anything change?" plus replay-keying, and the pre-snapshot is reconstructable from `snapshot_after - delta` if a future check needs it.
2. **Validator transport.** Rust used `tokio::sync::mpsc::channel(32)`. Python uses `asyncio.Queue(maxsize=32)`. Bounded; oldest-record drop on backpressure (faithful to original "lossy by design" intent).
3. **Console exporter dropped from `setup.py`.** No longer fits — `WatcherSpanProcessor` is the destination, console output is just noise. Gated behind `SIDEQUEST_OTEL_CONSOLE=1` for debug, default off.

### 2.2 Out of scope (explicit)

- No new dashboard panes — restoring data flow into existing tabs (Timeline, State, Subsystems, Timing, Console).
- No replay/persistence of `TurnRecord` (ADR-031 §"Consequences/Positive" mentions it as a future possibility; not building now).
- No Pennyfarthing-style HTTP OTLP receiver. Direct in-process span processor as today.
- No second-LLM validation. ADR-031's "God lifting rocks" prohibition stands — all checks are deterministic Python.

---

## 3. Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 1 — Transport (FastAPI, /ws/watcher)                  unchanged  │
├────────────────────────────────────────────────────────────────────────┤
│ Layer 2 — Agent Spans                                                  │
│   • turn_span() opens at dispatch entry; every other span is its child │
│   • Every dead SPAN_* in spans.py gets emission sites at the           │
│     documented module — ~80 sites total                                │
│   • Helpers grow as needed                                             │
├────────────────────────────────────────────────────────────────────────┤
│ Layer 3 — Narrative Validator (NEW in Python)                          │
│   • TurnRecord dataclass assembled at end of dispatch                  │
│   • Bounded asyncio.Queue → validator task                             │
│   • Five checks: entity ref, inventory, patch legality,                │
│     trope-beat alignment, subsystem exercise                           │
│   • Each check publishes one of:                                       │
│     validation_warning | subsystem_exercise_summary |                  │
│     coverage_gap | turn_complete                                       │
│   • json_extraction_result is owned by the translator (§6),            │
│     not the validator — it's directly derivable from span attrs        │
├────────────────────────────────────────────────────────────────────────┤
│ Translator (WatcherSpanProcessor)                                      │
│   • Routing table — span name → (event_type, component, extractor)     │
│   • Emits typed events on span close, IN ADDITION TO agent_span_close  │
│   • Single source of truth: SpanRoute entries colocated with constants │
│     in spans.py; router map auto-built from imports                    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Layer 2 — Span Emission Inventory

Every dead family from `spans.py` gets emission helpers + call sites at the documented module. Target Python module paths verified against the current `sidequest-server` tree.

### 4.1 Family table

| Family | Constants | Target module(s) | Notes |
|---|---|---|---|
| **turn root** | `SPAN_TURN`, all `SPAN_TURN_*` sub-spans | `server/session_handler.py` (root open), `server/dispatch/*` for sub-spans | `turn_span()` opens at the dispatch entry. Every other span this section adds is its child. **Most load-bearing item — without it, traces are orphaned.** |
| **narrator** | `SPAN_NARRATOR_SEALED_ROUND` | `server/dispatch/barrier.py` (or wherever sealed-letter barrier lives post-port) | One per sealed-round resolution |
| **orchestrator** | `_NARRATOR_SESSION_RESET`, `_GENRE_IDENTITY_INJECTION`, `_TACTICAL_GRID_INJECTION`, `_TROPE_BEAT_INJECTION`, `_PARTY_PEER_INJECTION`, `_LORE_FILTER` | `agents/orchestrator.py` | One span per injection type |
| **agent LLM pipeline** | `SPAN_TURN_AGENT_LLM_PROMPT_BUILD`, `_PARSE_RESPONSE` (`_INFERENCE` already live) | `agents/orchestrator.py` | Wrap existing inference call |
| **content** | `SPAN_CONTENT_RESOLVE` | `genre/resolver*.py` | High volume — confirm sampling rate before shipping |
| **trope** | `SPAN_TROPE_TICK`, `_TICK_PER`, `_ROOM_TICK`, `_ACTIVATE`, `_RESOLVE`, `_CROSS_SESSION`, `_EVALUATE_TRIGGERS` | `game/trope*.py` + `agents/subsystems/troper*.py` | |
| **barrier** | `SPAN_BARRIER_ACTIVATED`, `_RESOLVED` | `game/barrier*.py` | |
| **music** | `SPAN_MUSIC_EVALUATE`, `_CLASSIFY_MOOD` | `audio/` | |
| **persistence** | `SPAN_PERSISTENCE_SAVE`, `_LOAD`, `_DELETE` | `game/persistence*.py` | |
| **chargen** | `SPAN_CHARGEN_STAT_ROLL`, `_STATS_GENERATED`, `_HP_FORMULA`, `_BACKSTORY_COMPOSED` | `game/builder*.py` | |
| **NPC** | `SPAN_NPC_REGISTRATION`, `_MERGE_PATCH` (`_AUTO_REGISTERED`, `_REINVENTED` already live) | `server/dispatch/npc_registry.py`, `game/npc*.py` | |
| **creature** | `SPAN_CREATURE_HP_DELTA` | `game/creature*.py` | |
| **disposition** | `SPAN_DISPOSITION_SHIFT` | `game/disposition*.py` | |
| **state patches** | `SPAN_APPLY_WORLD_PATCH`, `SPAN_QUEST_UPDATE`, `SPAN_BUILD_PROTOCOL_DELTA`, `SPAN_COMPUTE_DELTA` | `game/state*.py`, `game/delta*.py` | The "what mutated" record — ADR-031 explicitly cites this as the patch-legality input |
| **merchant** | `SPAN_MERCHANT_CONTEXT_INJECTED`, `_TRANSACTION` | `agents/orchestrator.py`, `game/state*.py` | |
| **inventory** | `SPAN_INVENTORY_EXTRACTION` | `agents/inventory_extractor*.py` | Drives `json_extraction_result` typed event |
| **continuity** | `SPAN_CONTINUITY_LLM_VALIDATION` | `agents/continuity_validator*.py` | |
| **compose** | `SPAN_COMPOSE` | `agents/context_builder*.py` | Wraps prompt-zone composition |
| **world** | `SPAN_WORLD_MATERIALIZED` | `agents/world_builder*.py` | |
| **RAG** | `SPAN_RAG_PROSE_CLEANUP` | `agents/orchestrator.py` (or wherever lore retrieval landed) | |
| **script tool** | `SPAN_SCRIPT_TOOL_PROMPT_INJECTED` | `agents/orchestrator.py` | |
| **reminders** | `SPAN_REMINDER_SPAWNED`, `_FIRED` | `server/dispatch/connect.py`, `server/app.py` | |
| **pregen** | `SPAN_PREGEN_SEED_MANUAL` | `server/dispatch/pregen*.py` | |
| **catch-up** | `SPAN_CATCH_UP_GENERATE` | `server/dispatch/catch_up*.py` | |
| **scenario** | `SPAN_SCENARIO_ADVANCE`, `_ACCUSATION` | `server/dispatch/*.py`, `server/dispatch/slash*.py` | |
| **monster manual** | `SPAN_MONSTER_MANUAL_INJECTED` | `server/dispatch/*.py` | |

### 4.2 Implementation conventions

1. **Helper-first.** If a span has a `xxx_span()` context manager in `spans.py`, use it. If not, add the helper before adding call sites — keeps attribute schemas consolidated.
2. **Parent context.** Every span opens *inside* the active turn root. Where a subsystem fires outside a turn (persistence on save, pregen on background warmup), it opens its own root span; never orphaned.
3. **Attribute discipline.** ADR-031 §"Layer 2" lists required attributes per span family — every helper enforces those (positional kwargs) and accepts `**attrs` for extras. No bare `start_as_current_span` calls in domain code.
4. **No silent skips.** Per CLAUDE.md *No Silent Fallbacks*, an emission helper must fire every time it's reached. No `if span_enabled` flag, no `try/except` swallow.

---

## 5. Layer 3 — Narrative Validator Pipeline

### 5.1 `TurnRecord` dataclass

```python
@dataclass(frozen=True)
class PatchSummary:
    patch_type: str         # "world" | "combat" | "chase" | "scenario"
    fields_changed: list[str]

@dataclass(frozen=True)
class TurnRecord:
    turn_id: int
    timestamp: datetime
    player_id: str
    player_input: str
    classified_intent: str          # raw classification name
    agent_name: str
    narration: str
    patches_applied: list[PatchSummary]
    snapshot_before_hash: str       # blake2b of pre-turn snapshot
    snapshot_after: GameSnapshot    # full post-turn state
    delta: StateDelta               # what changed (already computed)
    beats_fired: list[tuple[str, float]]  # (trope_name, threshold)
    extraction_tier: int            # 1, 2, or 3
    token_count_in: int
    token_count_out: int
    agent_duration_ms: int
    is_degraded: bool
```

Lives at `sidequest/telemetry/turn_record.py`. Frozen dataclasses for immutability across the queue boundary.

### 5.2 Pipeline

```
Dispatch (hot path)                        Validator task (cold path)
────────────────────────                   ─────────────────────────────
session_handler.handle_action
    │
    ├─ orchestrator.process_action()
    │     (Layer-2 spans fire as today)
    │
    ├─ patches applied, delta computed
    │
    ├─ TurnRecord assembled
    │
    ├─ validator_queue.put_nowait(record) ──── asyncio.Queue(32) ───►  await queue.get()
    │     (drops oldest on QueueFull —                                   │
    │      log dropped_record_count via                                  ├─ entity_check
    │      watcher.health event)                                         ├─ inventory_check
    │                                                                    ├─ patch_legality_check
    │     ▼                                                              ├─ trope_alignment_check
    │  WS broadcast to player                                            ├─ subsystem_exercise_check
    │                                                                    │
    │                                                                    └─ publish_event(...)
    └─ next turn                                                            for each finding
```

**Lifecycle.** `validator_task` started by `app.py` at FastAPI startup, alongside the existing watcher hub binding. Single task, sequential processing. Validator allowed to lag — that's the point of the bounded queue. Validator never raises into hot path. Each check wraps in `try/except` that logs to `validation_warning` with `severity: "error"` and a check-name tag. On shutdown, the task drains with a 2s grace, then exits.

### 5.3 The five checks

Each runs against one `TurnRecord` and emits zero-or-more events via `publish_event`. Matches ADR-031's Rust catalog 1:1.

| Check | Reads | Emits when | Event type | Severity |
|---|---|---|---|---|
| **entity_check** | `narration`, `snapshot_after.npc_registry`, `discovered_regions`, `inventory.items` | Narration mentions an NPC name / item / location not in snapshot | `validation_warning` | `warning` |
| **inventory_check** | `narration`, `delta.inventory_changes`, `patches_applied` | Narration says "you grab the X" but no patch added X / patch added Y but narration silent | `validation_warning` | `warning` |
| **patch_legality_check** | `patches_applied`, `snapshot_after` | HP > max, dead NPC acts, location transition from a region not adjacent in cartography graph, illegal stat mutation | `validation_warning` | `error` |
| **trope_alignment_check** | `beats_fired`, `narration` | A beat threshold crossed but narration's keyword set doesn't reflect it (uses the trope's own `keywords` list — no second LLM call) | `validation_warning` | `warning` |
| **subsystem_exercise_check** | sliding window of last N turns, agent invocation history | Agent type X (combat / merchant / world_builder / scenario) hasn't been invoked in N turns | `coverage_gap` (periodic) + `subsystem_exercise_summary` (per-turn rollup) | `info` |

The validator also emits **`turn_complete`** as its first action upon dequeue, populating `TurnCompleteFields` from the assembled `TurnRecord`. The translator does not emit `turn_complete` from the span close — the validator has the full record, which is a strictly better source.

`json_extraction_result` is **not** a validator concern — it's emitted directly by the translator from `SPAN_INVENTORY_EXTRACTION` / `SPAN_TURN_AGENT_LLM_PARSE_RESPONSE` / `SPAN_CONTINUITY_LLM_VALIDATION` close, where the tier and outcome are span attributes. See §6.4.

### 5.4 Health & self-observation

The hub already exposes `stats()` (subscriber count, published, dropped). The validator task adds:

- `validator.queue_depth` — emitted every 30s as a `state_transition` with `component: "validator"`
- `validator.dropped_records` — incremented on `QueueFull`, surfaced in the heartbeat
- `validator.check_durations_ms` — per-check timing, p50/p99 over a sliding window

If the validator crashes the task is logged loudly and the hub publishes a `validation_warning` with `severity: "error"` describing the death — per *No Silent Fallbacks*, the operator knows if the lie detector itself is offline.

---

## 6. Translator Enrichment — Full Parity

### 6.1 Principle

Domain code's job is to **open a span with rich attributes**. The translator's job is to **emit the typed event(s)** on close. Direct `publish_event(...)` calls survive only for events that genuinely have no span (audio cue without state change, watcher self-health, etc.).

This collapses the ~30 scattered `publish_event("state_transition", ...)` sites into a single routing table.

### 6.2 Routing rule

For each span closed by `on_end`:
1. **Always** emit `agent_span_close` (Timeline / Timing tabs depend on the flat firehose).
2. **Additionally**, if the span's `name` matches a known route, emit a typed event derived from the span's attributes.

Augment, not replace.

### 6.3 Single-source-of-truth mechanics

```python
# spans.py — colocate the routing decision with the span constant
SPAN_DISPOSITION_SHIFT = "disposition.shift"
ROUTE_DISPOSITION_SHIFT = SpanRoute(
    event_type="state_transition",
    component="disposition",
    extract=lambda span: {
        "field": "disposition",
        "npc": span.attributes.get("npc", ""),
        "delta": int(span.attributes.get("delta", 0)),
    },
)
```

The router map in `watcher.py` is one auto-built dict from imports, not a parallel data source. Renaming a constant breaks at import; adding a span without a route is a lint check (Section 7).

### 6.4 Full routing table

#### → `state_transition`

The bulk of the mapping. Every span that mutates persistent game state routes here, with `component` carrying the subsystem.

| Span | component |
|---|---|
| `SPAN_APPLY_WORLD_PATCH` | `state.world` |
| `SPAN_QUEST_UPDATE` | `state.quest` |
| `SPAN_BUILD_PROTOCOL_DELTA` | `state.delta` |
| `SPAN_COMPUTE_DELTA` | `state.delta` |
| `SPAN_NPC_REGISTRATION` / `_AUTO_REGISTERED` / `_REINVENTED` / `_MERGE_PATCH` | `npc_registry` |
| `SPAN_DISPOSITION_SHIFT` | `disposition` |
| `SPAN_CREATURE_HP_DELTA` | `creature` |
| `SPAN_TROPE_TICK` / `_TICK_PER` / `_ROOM_TICK` / `_ACTIVATE` / `_RESOLVE` / `_CROSS_SESSION` / `_EVALUATE_TRIGGERS` | `trope` |
| `SPAN_BARRIER_ACTIVATED` / `_RESOLVED` | `barrier` |
| `SPAN_MERCHANT_TRANSACTION` / `_CONTEXT_INJECTED` | `merchant` |
| `SPAN_MUSIC_EVALUATE` / `_CLASSIFY_MOOD` | `audio` |
| `SPAN_PERSISTENCE_SAVE` / `_DELETE` | `persistence` |
| `SPAN_SCENARIO_ADVANCE` / `_ACCUSATION` | `scenario` |
| `SPAN_MONSTER_MANUAL_INJECTED` | `monster_manual` |
| `SPAN_REMINDER_SPAWNED` / `_FIRED` | `reminder` |
| `SPAN_PREGEN_SEED_MANUAL` | `pregen` |
| `SPAN_CATCH_UP_GENERATE` | `catch_up` |
| `SPAN_WORLD_MATERIALIZED` | `world_builder` |
| `SPAN_CHARGEN_STAT_ROLL` / `_STATS_GENERATED` / `_HP_FORMULA` / `_BACKSTORY_COMPOSED` | `chargen` |
| `SPAN_DICE_REQUEST_SENT` / `_THROW_RECEIVED` / `_RESULT_BROADCAST` | `dice` (events on span; router has dedicated event-handling branch) |
| `SPAN_MP_GAME_CREATED` / `_SLUG_CONNECT` / `_SEAT` / `_PLAYER_ACTION_PAUSED` | `multiplayer` |
| `SPAN_COMBAT_TICK` / `_ENDED` / `_PLAYER_DEAD` | `combat` |
| `SPAN_ENCOUNTER_PHASE_TRANSITION` / `_RESOLVED` / `_BEAT_APPLIED` / `_CONFRONTATION_INITIATED` / `_EMPTY_ACTOR_LIST` / `_BEAT_FAILURE_BRANCH` | `encounter` |
| `SPAN_ORCHESTRATOR_NARRATOR_SESSION_RESET` / `_GENRE_IDENTITY_INJECTION` / `_TACTICAL_GRID_INJECTION` / `_TROPE_BEAT_INJECTION` / `_PARTY_PEER_INJECTION` | `orchestrator` |
| `SPAN_SCRIPT_TOOL_PROMPT_INJECTED` | `script_tool` |
| `SPAN_NARRATOR_SEALED_ROUND` | `narrator` |
| `SPAN_LOCAL_DM_DECOMPOSE` / `_DISPATCH_BANK` / `_LETHALITY_ARBITRATE` | `local_dm` |
| `SPAN_PROJECTION_DECIDE` / `_CACHE_FILL` / `_CACHE_LAZY_FILL` | `projection` |

#### → `prompt_assembled`

| Span |
|---|
| `SPAN_COMPOSE` |
| `SPAN_TURN_AGENT_LLM_PROMPT_BUILD` |
| `SPAN_ORCHESTRATOR_PROCESS_ACTION` |

#### → `lore_retrieval`

| Span |
|---|
| `SPAN_RAG_PROSE_CLEANUP` |
| `SPAN_ORCHESTRATOR_LORE_FILTER` |

#### → `json_extraction_result`

| Span |
|---|
| `SPAN_INVENTORY_EXTRACTION` |
| `SPAN_TURN_AGENT_LLM_PARSE_RESPONSE` |
| `SPAN_CONTINUITY_LLM_VALIDATION` |

#### → `subsystem_exercise_summary`

| Span |
|---|
| `SPAN_LOCAL_DM_SUBSYSTEM` (also feeds the validator's coverage-gap check) |

#### Stays flat (`agent_span_close` only)

Timing data only, no semantic content. Listed in `FLAT_ONLY_SPANS`:

- `SPAN_TURN` — validator owns `turn_complete`
- `SPAN_AGENT_CALL` / `_SESSION` — Claude subprocess timing
- `SPAN_TURN_AGENT_LLM_INFERENCE` — LLM call duration
- `SPAN_TURN_SYSTEM_TICK` / `_BEAT_CONTEXT` — per-tick parents whose effects propagate via deeper spans
- `SPAN_TURN_BARRIER` / `_STATE_UPDATE` / `_TROPES` / `_PHASE_TRANSITION` / `_MEDIA` / `_ASSEMBLE` / `_SLASH_COMMAND` / `_PREPROCESS_*` — structural sub-turn spans
- `SPAN_CONTENT_RESOLVE` — high-volume genre-pack lookup (read, not state mutation); routing every call would spam the dashboard. Lookup failures should fire `validation_warning` separately

### 6.5 Severity inference

- OTEL `Status.code == ERROR` → severity `error`.
- `json_extraction_result` with `tier > 1` → severity `warning` (Claude needed fallback).
- `validation_warning` from the validator carries its own severity.
- All others default `info`.

### 6.6 Migration of existing `publish_event` sites

A one-time audit, done as part of the implementation plan:

```
For each publish_event("state_transition", ..., component=X) site in
sidequest/server/{narration_apply,session_handler,session_helpers}.py:
  1. Identify the surrounding span (if any).
  2. If the site is INSIDE a span whose constant is in the routing table:
       — Remove the publish_event call.
       — Move any extra fields onto the span as attributes.
  3. If the site has NO surrounding span:
       — Either add an emission helper (preferred), OR
       — Keep the direct publish_event (sideband: watcher.health,
         audio cue without state mutation, etc.).
       — Document which one and why in the PR.
```

End state: every `state_transition` event the dashboard receives is either router-emitted from a span close or explicitly direct-emitted from a documented sideband site.

### 6.7 Final ownership matrix

| `WatcherEventType` | Owner | Mechanism |
|---|---|---|
| `agent_span_open` | watcher hub | WS handshake (existing) |
| `agent_span_close` | translator | every span close (existing, augmented) |
| `state_transition` | **translator** primary + sideband direct emits | router covers ~50 span families; direct emits only where span-less |
| `game_state_snapshot` | domain code | `session_handler.py` (existing) |
| `prompt_assembled` | translator | 3 span families |
| `lore_retrieval` | translator | 3 span families |
| `json_extraction_result` | translator | 3 span families |
| `subsystem_exercise_summary` | translator | `local_dm.subsystem` close |
| `coverage_gap` | validator | subsystem-exercise check (sliding window) |
| `validation_warning` | validator | 5 narrative checks |
| `turn_complete` | validator | one per `TurnRecord` |

Every `WatcherEventType` has a clear owner. No orphans; no double-emission.

---

## 7. Testing Strategy

CLAUDE.md is non-negotiable: *"Every Test Suite Needs a Wiring Test."* Tests passing in isolation has been the failure mode of the dashboard regression itself.

### 7.1 Three layers of test coverage

#### Layer 1 — Unit: span helpers behave

For every helper added or expanded in `spans.py`:
- Asserts the context manager opens a span with the named constant.
- Asserts every required positional kwarg becomes a span attribute.
- Asserts an extras `**attrs` dict merges in.
- Asserts a provider-local `_tracer` parameter is honored.

Extends existing patterns in `tests/telemetry/test_spans.py`, `test_combat_encounter_spans.py`, `test_lethality_span.py`.

#### Layer 2 — Translator: routing produces typed events

In `tests/server/test_watcher_events.py` (extended):

```python
@pytest.mark.parametrize("span_const,expected_event_type,expected_component", [
    (SPAN_DISPOSITION_SHIFT,    "state_transition",       "disposition"),
    (SPAN_INVENTORY_EXTRACTION, "json_extraction_result", "sidequest-server"),
    (SPAN_COMPOSE,              "prompt_assembled",       "sidequest-server"),
    # ... one row per routed span
])
def test_translator_emits_typed_event(span_const, expected_event_type, expected_component):
    """Closing <span_const> publishes a typed event AND agent_span_close."""
```

One row per entry in the routing table.

#### Layer 3 — Wiring: production code actually fires the spans

For each subsystem family in §4.1, **one integration test** that:
1. Subscribes a fake WebSocket to `watcher_hub`.
2. Drives a representative production code path.
3. Asserts the expected typed event(s) land on the fake WS, with the expected `component` and shape.

Example:

```python
async def test_disposition_shift_emits_state_transition(server_fixture):
    fake_ws = FakeWatcher()
    await watcher_hub.subscribe(fake_ws)

    await server_fixture.dispatch_action(
        player="alice",
        text="I help the wounded merchant.",
    )

    events = fake_ws.events
    assert any(
        e["event_type"] == "state_transition" and e["component"] == "disposition"
        for e in events
    ), "disposition.shift span never reached the watcher hub"
```

~25 wiring tests, one per subsystem family. Medium-cost (boot a session) but the only protection against the failure mode that caused this entire spec.

### 7.2 Static lint check — every span is routed or explicitly skipped

A new `tests/telemetry/test_routing_completeness.py`:

```python
def test_every_span_is_routed_or_explicitly_flat():
    """Fail if a SPAN_* constant lacks both a routing entry and a flat-only marker."""
    flat_only = set(FLAT_ONLY_SPANS)
    routed = set(SPAN_ROUTES.keys())
    all_spans = {v for n, v in vars(spans).items() if n.startswith("SPAN_")}
    missing = all_spans - flat_only - routed
    assert not missing, f"Spans without routing decision: {missing}"
```

Runs on every CI job. A new span constant cannot land without a routing decision.

### 7.3 Validator-pipeline tests

In a new `tests/telemetry/test_validator_pipeline.py`:
- **Lifecycle:** validator starts on app startup, drains on shutdown, restarts cleanly under uvicorn `--reload`.
- **Backpressure:** queue full → oldest record drops, drop counter increments, hub publishes a `validation_warning` after N drops.
- **Crash containment:** make one check raise → other checks still run, validator task survives, `validation_warning` with `severity: "error"` describes the crash.
- **Per-check fixtures:** for each of the five checks, a `TurnRecord` fixture that *should* trigger the warning and one that shouldn't.

### 7.4 P0 smoke test

The `just otel` recipe gets a one-line CI check:

```yaml
- name: just otel recipe smoke
  run: timeout 5 just otel || [[ $? -eq 124 ]]
  # exit 124 = timeout fired = recipe started successfully and is listening
```

Catches recipe-vs-script-name drift permanently.

### 7.5 Out of scope

- No replay tests (`TurnRecord` persistence not built).
- No GM panel UI tests for new tabs (existing UI tests assert on the dashboard contract; once data flows, they pass without modification).
- No load tests for the watcher hub (real playtests have ≤5 watchers; fan-out is `O(subscribers)`).

---

## 8. Sequencing

Stories framed for the sprint tracker. Calendar-day estimates suppressed in favor of PR counts at AI-era velocity.

### Phase 0 — Stop the bleed (1 PR, blocks nothing)

1. Fix `justfile` `otel` recipe → `playtest_dashboard.py`.
2. Drop `ConsoleSpanExporter` from `telemetry/setup.py` (gate behind `SIDEQUEST_OTEL_CONSOLE=1`).
3. Delete the stale "Phase 0 console exporter" docstring in `setup.py`.
4. CI smoke test for `just otel`.

Lands first so playtests aren't blocked by the missing recipe.

### Phase 1 — Translator routing infrastructure (1 PR, blocks Phase 2/3)

1. Add `SpanRoute` dataclass and the `SPAN_ROUTES` dict mechanism to `spans.py`.
2. Refactor `WatcherSpanProcessor.on_end` to use the router (still augment-not-replace).
3. Add the routing-completeness lint test (`test_routing_completeness.py`).
4. Add `FLAT_ONLY_SPANS` set with current live spans listed (so the lint passes immediately).

### Phase 2 — Layer-2 emission family PRs (~25 PRs, parallelizable)

One PR per subsystem family from §4.1. Each PR contains:
- Helper additions/expansions in `spans.py`.
- `SpanRoute` entries (or `FLAT_ONLY_SPANS` additions for timing-only spans).
- Emission sites in the target Python module.
- Translator-routing test rows.
- One wiring integration test.
- Migration of any existing direct `publish_event` site that the new span subsumes.

PRs are independent except: **`turn_span` lands first**. Mark the rest blocked-by `turn_span` until that ships.

Order suggestion after `turn`: high-volume / high-mechanic-trust families first (state patches, NPC, trope, encounter). Cosmetic ones last (chargen, world_materialized).

**Final call on PR-bundling deferred to the implementation plan.** Recommendation: bundle by adjacent module — fewer PRs, cleaner reviews, no inter-PR test interference.

### Phase 3 — Layer-3 validator pipeline (1 PR)

1. `TurnRecord` dataclass in `sidequest/telemetry/turn_record.py`.
2. `Validator` class with bounded `asyncio.Queue` and the five checks in `sidequest/telemetry/validator.py`.
3. Lifecycle wiring in `server/app.py`.
4. Health emissions (`validator.queue_depth`, `validator.dropped_records`, `validator.check_durations_ms`).
5. Test suite per §7.3.

Independent of Phase 2's rollout — validator runs on whatever spans have been wired so far.

### Phase 4 — Sweep & cleanup (1 PR)

1. Audit final list of remaining direct `publish_event` sites; confirm each has a documented sideband rationale or is removed.
2. Update `sidequest-ui/src/types/watcher.ts` comment "Mirrors Rust WatcherEventType (sidequest-server/src/lib.rs)" → point at `sidequest-server/sidequest/telemetry/spans.py + server/watcher.py`. Pure docstring fix.
3. Mark ADR-031 `implementation-status: live` for real this time.

---

## 9. Deliverables

| File | Action |
|---|---|
| `docs/superpowers/specs/2026-04-25-otel-dashboard-restoration-design.md` | New (this spec) |
| `docs/adr/089-otel-dashboard-restoration.md` | New (ADR) |
| `docs/adr/031-game-watcher-semantic-telemetry.md` | Amend (Python-port section + status note) |
| `CLAUDE.md` ADR Index block | Regenerated via `scripts/regenerate_adr_indexes.py` |
| `justfile` | Phase 0: fix `otel` recipe path |
| `sidequest-server/sidequest/telemetry/setup.py` | Phase 0: drop ConsoleExporter; rewrite docstring |
| `sidequest-server/sidequest/telemetry/spans.py` | Phase 1: SpanRoute mechanism. Phase 2: ~25 helper additions, route entries |
| `sidequest-server/sidequest/server/watcher.py` | Phase 1: router-driven `on_end` |
| `sidequest-server/sidequest/telemetry/turn_record.py` | Phase 3: NEW |
| `sidequest-server/sidequest/telemetry/validator.py` | Phase 3: NEW |
| `sidequest-server/sidequest/server/app.py` | Phase 3: wire validator lifecycle |
| `sidequest-server/sidequest/{game,agents,server}/**/*.py` | Phase 2: emission sites at ~25 modules |
| `sidequest-server/tests/telemetry/test_routing_completeness.py` | Phase 1: NEW lint test |
| `sidequest-server/tests/telemetry/test_validator_pipeline.py` | Phase 3: NEW |
| `sidequest-server/tests/server/test_watcher_events.py` | Extended with translator parametrize rows |
| `sidequest-server/tests/integration/test_subsystem_wiring.py` (or per-family files) | Phase 2: ~25 wiring tests |

## 10. ADR linkage

- **ADR-089 (new):** *OTEL Dashboard Restoration after Python Port.* Status `accepted`. Documents the three-layer faithful-port decision, the deliberate departures, and the routing-table-as-single-source-of-truth pattern. Supersedes nothing; `related: [031, 058, 082]`.
- **ADR-031 amendment:** add a Python-port section noting the canonical implementation now lives in `sidequest/telemetry/spans.py` and `sidequest/server/watcher.py`. Strikethrough the Rust-specific phasing table. Re-affirm `implementation-status: live`.
- **CLAUDE.md ADR Index:** insert ADR-089 under "Telemetry" alongside ADR-031, ADR-058. Run `scripts/regenerate_adr_indexes.py`.

## 11. What this design does NOT decide

Deliberately deferred to the implementation plan (next skill, `superpowers:writing-plans`):
- Exact per-helper kwarg lists for the ~25 new emission helpers.
- Exact per-route field-extractor function bodies.
- Per-PR Jira-equivalent story IDs and titles.
- Whether Phase 2's ~25 PRs are bundled into mega-PRs by domain or stay one-per-span.

---

*End of design.*
