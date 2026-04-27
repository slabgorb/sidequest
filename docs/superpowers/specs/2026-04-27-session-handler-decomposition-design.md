# Spec — `session_handler.py` Decomposition

**Date:** 2026-04-27
**Author:** Architect (Leonard of Quirm)
**Status:** Approved (brainstorm)
**Related:** ADR-063 (Dispatch Handler Splitting), ADR-082 (Rust→Python port)
**Supersedes:** `docs/design/session-handler-decomposition.md` (delete when this spec lands)

## Problem

`sidequest-server/sidequest/server/session_handler.py` is **5458 lines**. It is the top-level coordinator that ADR-063 left in place after the dispatch pipeline was extracted into `server/dispatch/`. Since the post-port amendment to ADR-063 (2026-04-23) it has accreted concerns that ADR-063's principle ("each module has one job in the sequence") explicitly assigned outside the coordinator:

- A 1000-line connect handler
- A 665-line narration-turn execution method
- A 495-line chargen-confirmation method
- View projection, event emission, media dispatch, lore/embed worker logic

The coordinator itself is now too big to coordinate. This spec defines the implementation phasing for ADR-063's post-port sequel: extracting eight clusters of behavior into sibling modules while preserving byte-identical behavior.

## Decision (recap from brainstorm)

- **Scope:** All eight phases specified at design level. Each phase ships as one story, merged before the next starts.
- **Extraction pattern:** Free function with `handler: WebSocketSessionHandler` as first argument. No new abstractions, no class hierarchies, no DI containers, no event bus, no narrow context dataclasses (premature for this churn).
- **End state:** `WebSocketSessionHandler` ~700 lines containing only lifecycle, message dispatch, cleanup, and `_SessionData`.
- **Behavior:** Identical pre/post extraction. Existing integration tests pass without modification.

## Architecture

### Module Layout (target end state)

```
sidequest-server/sidequest/server/
├── session_handler.py             # ~700 lines — coordinator + _SessionData
├── emitters.py                    # NEW (Phase 1)
├── views.py                       # NEW (Phase 2)
├── dispatch/
│   ├── __init__.py                # existing
│   ├── chargen_loadout.py         # existing
│   ├── chargen_summary.py         # existing
│   ├── combat_brackets.py         # existing
│   ├── confrontation.py           # existing
│   ├── culture_context.py         # existing
│   ├── dice.py                    # existing
│   ├── encounter_lifecycle.py     # existing
│   ├── map_update.py              # existing
│   ├── opening_hook.py            # existing
│   ├── scenario_bind.py           # existing
│   ├── sealed_letter.py           # existing
│   ├── yield_action.py            # existing
│   ├── lore_embed.py              # NEW (Phase 3)
│   ├── media.py                   # NEW (Phase 4)
│   └── narration_turn.py          # NEW (Phase 8)
└── handlers/
    ├── __init__.py                # NEW
    ├── chargen.py                 # NEW (Phase 5)
    ├── messages.py                # NEW (Phase 6)
    └── connect/                   # NEW (Phase 7 sub-package)
        ├── __init__.py            # exports handle_connect()
        ├── slug_resolve.py        # modern slug path
        ├── legacy_resolve.py      # deprecated genre+world path (kept until callers removed)
        ├── pack_bind.py
        ├── save_open.py
        ├── session_restore.py
        ├── orchestrator_init.py
        ├── chargen_init.py        # includes opening-hook resolution (small, adjacent)
        ├── world_context.py
        └── first_emit.py
```

### Extraction Pattern

```python
# server/emitters.py
def emit_event(handler: WebSocketSessionHandler, kind: str, payload_model: object) -> object:
    """Build, project, and record a SentFrame.

    Extracted from WebSocketSessionHandler._emit_event.
    Implementation moved verbatim — no behavior change.
    """
    ...
```

The handler is passed by reference. All state on `self` remains reachable. Caller-side delegation in `session_handler.py`:

```python
class WebSocketSessionHandler:
    def _emit_event(self, kind: str, payload_model: object) -> object:
        return emitters.emit_event(self, kind, payload_model)
```

The thin delegate stays during the transition. Once all callers within `session_handler.py` use the free function directly, the delegate can be removed in a follow-up cleanup story (not part of this epic).

## Phase-by-Phase Specification

### Phase 1 — Event Emission → `server/emitters.py`

**Source methods:** `_emit_event` (file:918), `_emit_scrapbook_entry` (file:1076), `_emit_map_update_for_cartography` (file:1207), `_persist_scrapbook_entry` (file:1336)
**Approx lines moved:** 460
**Risk:** Low

**Public surface:**
```python
def emit_event(handler, kind: str, payload_model: object) -> object
def emit_scrapbook_entry(handler, result: NarrationTurnResult) -> object | None
def emit_map_update_for_cartography(handler, sd: _SessionData) -> None
def persist_scrapbook_entry(handler, payload: ScrapbookEntryPayload) -> None
```

**Acceptance criteria:**
- All four functions live in `emitters.py` with identical behavior to current methods
- `WebSocketSessionHandler._emit_event` (and siblings) remain as thin delegates calling the free functions
- `tests/server/test_emitters.py` exists with at least one test per function
- One wiring test confirms `WebSocketSessionHandler._emit_event` calls `emitters.emit_event`
- Pre/post grep of OTEL span emissions in `session_handler.py` shows the spans now live in `emitters.py` (count preserved)
- All existing server integration tests pass without modification

### Phase 2 — View Projection → `server/views.py`

**Source methods:** `_is_hidden_status_list` (file:671), `_build_game_state_view` (file:674), `status_effects_by_player` (file:801), `_backfill_last_narration_block` (file:832), `_party_member_from_character` (file:5247), `_resolve_self_character` (file:5336), `_build_session_start_party_status` (file:5370)
**Approx lines moved:** 460
**Risk:** Low

**Public surface:**
```python
def build_game_state_view(handler) -> SessionGameStateView
def status_effects_by_player(handler) -> dict[str, list[str]]
def backfill_last_narration_block(handler, snapshot, ...) -> NarrationBlock | None
def party_member_from_character(handler, character: Character) -> PartyMember
def resolve_self_character(handler, sd: _SessionData) -> Character | None
def build_session_start_party_status(handler, sd: _SessionData) -> PartyStatusPayload
```

**Acceptance criteria:** Same shape as Phase 1.

### Phase 3 — Lore / Embed Worker → `server/dispatch/lore_embed.py`

**Source methods:** `_retrieve_lore_for_turn` (file:4869), `_dispatch_embed_worker` (file:4904), `_run_embed_worker` (file:4946)
**Approx lines moved:** 110
**Risk:** Low

**Public surface:**
```python
async def retrieve_for_turn(handler, sd: _SessionData, action: str) -> str | None
def dispatch_worker(handler, sd: _SessionData) -> None
async def run_worker(handler, sd: _SessionData) -> None  # internal task body
```

**Acceptance criteria:** Same shape. Preserve `embed_task` lifecycle on `_SessionData` exactly — cancellation in `cleanup` must still work.

### Phase 4 — Media Dispatch → `server/dispatch/media.py`

**Source methods:** `_build_audio_backend` (file:4451), `_maybe_dispatch_render` (file:4507), `_maybe_dispatch_audio` (file:4758), `_audio_skip` (file:4830), `_audio_dispatched` (file:4849), `_run_render` (file:4979)
**Approx lines moved:** 700
**Risk:** Medium

**Public surface:**
```python
def build_audio_backend(handler, sd: _SessionData) -> LibraryBackend | None
def maybe_dispatch_render(handler, sd: _SessionData, result: NarrationTurnResult) -> None
def maybe_dispatch_audio(handler, sd: _SessionData, result: NarrationTurnResult) -> None
def audio_skip(handler, reason: str) -> None
def audio_dispatched(handler, scene_id: str) -> None
async def run_render(handler, sd: _SessionData, ...) -> None  # task body
```

**Acceptance criteria:** Same shape. ADR-050 image pacing throttle on `_SessionData` is read by `maybe_dispatch_render`; do not re-touch the throttle. Daemon-client interactions preserved verbatim.

### Phase 5 — Character Creation → `server/handlers/chargen.py`

**Source methods:** `_handle_character_creation` (file:2673), `_chargen_scene` (file:2771), `_chargen_continue` (file:2822), `_resolve_character_archetype` (file:2841), `_chargen_confirmation` (file:2926), `_next_message` (file:3421)
**Approx lines moved:** 770
**Risk:** Medium

**Public surface:**
```python
async def handle_character_creation(handler, msg: GameMessage) -> list[object]
def chargen_scene(handler, sd: _SessionData) -> object  # internal helper
def chargen_continue(handler, sd: _SessionData, ...) -> object  # internal helper
def resolve_character_archetype(handler, sd: _SessionData, choices) -> ResolvedArchetype
async def chargen_confirmation(handler, sd: _SessionData) -> list[object]
def next_message(handler, sd: _SessionData) -> object
```

**Acceptance criteria:** Same shape. The `_chargen_confirmation` 495-line block stays whole within this story (further sub-decomposition is a future story if needed). MP-aware behavior (peer-already-committed branch) preserved exactly. Lore seeding, NPC registry reset, scenario-pack binding, opening-turn bootstrap all stay in their current order.

### Phase 6 — Small Message Handlers → `server/handlers/messages.py`

**Source methods:** `_handle_player_seat` (file:1473), `_handle_dice_throw` (file:1528), `_handle_yield` (file:1633), `_handle_session_event` (file:1663)
**Approx lines moved:** 200
**Risk:** Low

**Public surface:**
```python
def handle_player_seat(handler, msg: GameMessage) -> list[object]
async def handle_dice_throw(handler, msg: GameMessage) -> list[object]
def handle_yield(handler, msg: GameMessage) -> list[object]
async def handle_session_event(handler, msg: GameMessage) -> list[object]
```

**Acceptance criteria:** Same shape. Note `handle_dice_throw` already calls into `dispatch/dice.py` for the dispatcher — that boundary is unchanged; we are only moving the WebSocket-message wrapper.

### Phase 7 — Connect → `server/handlers/connect/` (sub-package)

**Source method:** `_handle_connect` (file:1673–2673, ~1000 lines)
**Approx lines moved:** 1000
**Risk:** High

This is the largest single extraction and the only one that requires a sub-package. The decomposition follows the existing internal section markers in `_handle_connect`.

**Sub-stage layout:**

Source method spans absolute file lines 1673–2672. The dominant chunk is the slug-or-legacy resolution branch at the top of the method (~756 lines); everything below ~file:2434 is post-resolution shared work composed of small, well-bounded steps.

| Stage | Absolute line range | Module | Function |
|---|---|---|---|
| A. Slug-or-legacy resolve | 1673–2433 | `slug_resolve.py` | `resolve_slug_or_legacy(handler, msg) -> SlugResolution` |
| B. Pack bind | 2434–2445 | `pack_bind.py` | `load_genre_pack(handler, resolution) -> GenrePack` |
| C. Save open | 2446–2453 | `save_open.py` | `open_or_create_store(handler, resolution) -> SqliteStore` |
| D. Session restore | 2454–2515 | `session_restore.py` | `load_or_init(handler, store, ...) -> GameSnapshot` |
| E. Orchestrator init | 2516–2518 | `orchestrator_init.py` | `build_orchestrator(handler, sd) -> Orchestrator` |
| F. Chargen + opening init | 2519–2546 | `chargen_init.py` | `init_builder_and_opening(handler, sd) -> None` (folds the opening-hook resolution at file:2532–2546 since it is small and topically adjacent) |
| G. World context | 2547–2589 | `world_context.py` | `resolve_world_context(handler, sd) -> str \| None` |
| H. First emit | 2590–2672 | `first_emit.py` | `emit_chargen_or_resume(handler, sd) -> list[object]` |

**Stage A note — internal complexity.** Stage A is ~760 lines (slug path + legacy path + shared post-branch normalization). It will not fit cleanly into a single 760-line module without further sub-decomposition. During Phase 7 implementation, the Architect (or Dev with architect consult) must split Stage A into at least:

- `slug_resolve.py` — the modern slug-based path (game lookup, mode determination, has_character probe)
- `legacy_resolve.py` — the deprecated genre+world path (kept until the legacy callers are removed)
- A shared dispatcher that picks the path and returns a unified `SlugResolution`

The exact split is deferred to Phase 7's implementation plan. Spec acceptance for Phase 7 requires that Stage A is decomposed *somehow* into modules ≤ 300 lines each, not that it remains a single 760-line file.

`handlers/connect/__init__.py` exposes `handle_connect(handler, msg) -> list[object]` — the orchestrator that calls all eight sub-stages in order. Approx 80 lines.

**Public surface (top-level):**
```python
async def handle_connect(handler, msg: GameMessage) -> list[object]
```

The eight sub-stages are package-private (importable from within `handlers/connect/` only).

**Acceptance criteria:**
- All Stage B–H sub-stage functions live in their named modules
- Stage A is decomposed into at least `slug_resolve.py` + `legacy_resolve.py` + a shared dispatcher; no single resulting module exceeds 300 lines
- `handle_connect` orchestrates the stages in the same order as the original method
- Branch logic (slug-vs-legacy, has_character true/false, schema-incompatible save) preserved exactly
- One unit test per sub-stage module in `tests/server/handlers/connect/`
- Wiring tests confirm `handle_connect` calls each sub-stage
- All existing connect-flow integration tests pass without modification
- OTEL span surface preserved (especially `mp_slug_connect_span`, lobby spans)
- Smoke playtest confirms reconnect, fresh-start, and chargen-resume paths all work

### Phase 8 — Narration Turn → `server/dispatch/narration_turn.py`

**Source methods:** `_handle_player_action` (file:3443), `_execute_narration_turn` (file:3638), `_run_opening_turn_narration` (file:4303)
**Approx lines moved:** 1000
**Risk:** High

This is the deepest pipeline in the system. Extraction follows the existing internal `TurnContext` seam.

**Public surface:**
```python
async def handle_player_action(handler, msg: GameMessage) -> list[object]
async def execute_turn(handler, sd: _SessionData, action: str, ...) -> list[object]
async def run_opening_turn(handler, sd: _SessionData) -> list[object]
```

**Internal pipeline functions** (private to `narration_turn.py`):
```python
def build_turn_context(handler, sd, action) -> TurnContext
async def retrieve_lore(handler, sd, action) -> str | None        # delegates to lore_embed.retrieve_for_turn
async def run_orchestrator(handler, sd, ctx) -> NarrationTurnResult
def apply_result(handler, sd, result) -> NarrationApplyOutcome    # delegates to narration_apply
def dispatch_post_turn_media(handler, sd, result) -> None         # delegates to media.maybe_dispatch_*
def dispatch_post_turn_embed(handler, sd) -> None                 # delegates to lore_embed.dispatch_worker
def emit_response_frames(handler, sd, result, outcome) -> list[object]  # uses emitters.emit_event
```

**Acceptance criteria:**
- Three top-level functions match existing method behavior byte-for-byte
- Internal pipeline preserves order: build context → lore retrieve → orchestrator run → apply → media → embed → emit
- All cross-cluster delegations (to Phase 1, 3, 4) work — Phase 8 cannot land before its dependencies
- OTEL span coverage preserved (turn_span, agent_call_span, persistence_save_span)
- Smoke playtest confirms a full narration turn produces identical narration, identical state changes, identical OTEL output

## Test Strategy

### Per-cluster unit tests

Each new module gets `tests/server/test_<module>.py` (or a subdirectory for connect). Tests construct a real `WebSocketSessionHandler` from existing fixture builders rather than mocking — the integration boundary is what we are protecting, not isolation. Mocking is acceptable only for the daemon client, the LLM client, and outbound queues.

### Wiring guard (mandatory per cluster)

Each PR adds at least one test that:
1. Imports the new free function
2. Monkeypatches it on its module
3. Calls the coordinator method
4. Asserts the patched function was called with expected arguments

This satisfies CLAUDE.md's rule: **"Every Test Suite Needs a Wiring Test."** Without it, an extracted function can become orphaned the next time someone edits the coordinator.

### Behavior pinning

Existing server integration tests must pass without modification through every phase. If a PR needs to change those tests, that is a code-smell and the PR must stop and reconsider. The only acceptable reason to modify an integration test during this epic is a pre-existing test bug surfaced by the change.

### OTEL parity

Every PR includes a before/after grep showing identical OTEL span surface:

```bash
grep -nE "tracer\.start_as_current_span|emit_[a-z_]+_span" sidequest-server/sidequest/server/session_handler.py
```

The post-extraction count in `session_handler.py` shrinks; the count in the new module rises by exactly the same amount. Smoke playtest confirms the GM panel sees the same telemetry.

## Error Handling & Concurrency

- **Async ordering preserved verbatim.** No fire-and-forget changes. The `embed_task` lifecycle stays on `_SessionData`; `cleanup` still cancels it.
- **Exception handlers move with their code.** The `# noqa: BLE001 — persistence failure must not block emit` block in `_emit_scrapbook_entry` moves intact to `emitters.py`.
- **No silent fallbacks added.** Per CLAUDE.md, any extracted function that previously raised, still raises. No new try/except wrappers introduced during extraction. If extraction surfaces a missing error handler, that is a bug to log but NOT to fix in this epic.
- **No backward-compatibility shims.** Once a method is extracted and the thin delegate is the only caller in `session_handler.py`, the delegate stays for the duration of this epic to keep diffs small. Removal happens in a follow-up cleanup story.

## Out of Scope

- `_SessionData` itself (shared state — stays put).
- Module-level helpers at top of `session_handler.py` (file:1–579) — already free functions, mostly already exported.
- Existing `dispatch/` package modules — already extracted by ADR-063 post-port. Do not re-touch.
- Any behavioral change. Pure decomposition only.
- Multi-genre / multi-mode / new feature work.
- Removal of thin delegate methods on `WebSocketSessionHandler` (follow-up cleanup story).
- Sub-decomposition of `_chargen_confirmation`'s 495-line block (future story if needed).

## Phasing — Story Sequence

| # | Cluster | Δ lines | Cumulative | Depends on |
|---|---|---|---|---|
| 1 | Event emission | -460 | ~5000 | none |
| 2 | View projection | -460 | ~4540 | none (parallel-mergeable with #1 in principle, but ship sequentially) |
| 3 | Lore / embed | -110 | ~4430 | none |
| 4 | Media dispatch | -700 | ~3730 | none |
| 5 | Chargen | -770 | ~2960 | none |
| 6 | Small message handlers | -200 | ~2760 | none |
| 7 | Connect | -1000 | ~1760 | none |
| 8 | Narration turn | -1000 | ~760 | **Phases 1, 3, 4** must merge first |

Phase 8 is the only phase with hard predecessor dependencies. All other phases are theoretically parallel-mergeable but should ship sequentially to keep merge surface small and to compound confidence in the extraction pattern.

## Open Items for SM

1. **Story sizing:** Phases 1–6 ≈ 3 points each. Phase 7 ≈ 5–8 points (sub-package). Phase 8 ≈ 5–8 points (cross-cluster delegation, async pipeline). Total epic ≈ 30–40 points.
2. **In-flight conflicts:** Before starting Phase 1, SM should `git log --since="14 days" -- sidequest-server/sidequest/server/session_handler.py` to check for active work that would conflict.
3. **Sequel decisions:** After Phase 8 lands, SM evaluates whether `_chargen_confirmation` warrants its own sub-decomposition story.
4. **Cleanup story:** Schedule a follow-up to remove the thin delegate methods on `WebSocketSessionHandler` once the epic completes. Out of scope here.
