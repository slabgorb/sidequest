---
story_id: "61-1"
jira_key: "none"
epic: "61"
workflow: "tdd"
---
# Story 61-1: Wire LoreStore into production ToolContext (ADR-048 Phase E)

## Story Details
- **ID:** 61-1
- **Epic:** 61 — Bounded Narrator Prompt: Slim Snapshot + Wire RAG
- **Workflow:** tdd
- **Repo:** sidequest-server
- **Points:** 3
- **Priority:** p0
- **Stack Parent:** none

## Acceptance Criteria

1. `LoreStore` instance from `session_handler.lore_store` is threaded into `ToolContext.lore_store` at the per-turn call site(s).
2. The early-return-empty branch in `agents/tools/query_lore.py:96-109` no longer fires in production. Verify: `lore_store_wired=False` field is removed from response after fix.
3. Query result carries real top-k fragments, not an empty array.
4. Integration test verifies `query_lore` tool returns populated results when called through the live orchestrator path (not a stub/mock).
5. OTEL watcher span emits (per ADR-031) show lore retrieval participating in the tool-loop.

## Technical Context

### The Problem

ADR-048 defined a complete Lore RAG Store architecture:
- `sidequest/game/lore_store.py` — `LoreStore` class (RAG store implementation)
- `sidequest/agents/tool_registry.py:99-104` — `ToolContext` has a field `lore_store: LoreStore | None = None`
- `sidequest/agents/tools/query_lore.py` — the `@tool` definition, with SDR schema

However, at the per-turn `ToolContext` construction site, the `session_handler.lore_store` (which exists at `sidequest/server/session_handler.py:485`) is never passed into `ToolContext`. Result: the tool returns empty (`{"fragments": [], "lore_store_wired": False}`) on every production call, and narrator narrates based on the full unslimmed lore corpus in the prompt instead of retrieving on demand.

### The Fix

Identify where `ToolContext` is instantiated in the per-turn code path (likely in `orchestrator.py` or `tool_registry.py` at the SDK call site) and thread `session_handler.lore_store` into it.

**Key locations:**
- `sidequest/server/session_handler.py:485` — `lore_store: LoreStore = field(default_factory=LoreStore)` (the owner)
- `sidequest/agents/tool_registry.py:99-104` — `ToolContext` definition
- `sidequest/agents/tools/query_lore.py:96-109` — the early-return-empty guard (to be eliminated)
- `sidequest/agents/orchestrator.py` — where `complete_with_tools()` builds the context for the SDK call

This story unblocks 61-2 (snapshot slim), which depends on RAG actually working before deciding which fields route through it.

## Workflow Tracking

**Workflow:** tdd
**Phase:** red (no work performed — wiring already shipped under 24-10)
**Phase Started:** 2026-05-23

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-23 | 2026-05-23 | <1d |
| red   | 2026-05-23 | -          | -    |

## Red phase

### Result: NO-OP — story is already implemented on develop

The wiring this story commissions was landed on develop 2026-05-21 (two days
before the epic-61 brief was drafted) under **commit 06ad79c
`feat(24-10): wire world-grounding loaders + ToolContext fields at bootstrap`**.
That commit threaded `lore_store`, `monster_manual`, and the world-grounding
trio (`weather_state` / `world_demographics` / `world_calendar`) through
`TurnContext` and the per-turn `ToolContext` construction site in one pass.
The epic-61 brief was written against a stale read of the code that pre-dated
24-10's landing.

### Verification — the two wire seams are already in place

1. `sidequest/server/session_helpers.py:714-748` — `_build_turn_context`
   stamps `lore_store=sd.lore_store` onto the `TurnContext` it returns. The
   inline comment block at 727-737 explicitly references the bug this story
   is meant to fix (`"query_lore returned hit_count=0 every turn"`) and
   documents the fix as landed.
2. `sidequest/agents/orchestrator.py:3491-3521` — the per-turn `ToolContext`
   constructor inside `_run_narration_turn_sdk` reads
   `lore_store=context.lore_store`. The inline comment at 3499-3501 calls
   this "THE fix for `query_lore` hit_count=0" and the positive-wiring OTEL
   span at 3530-3541 emits `narration.turn.lore_fragments` so the GM panel
   can see the count was carried through the seam.

No production call site constructs a `ToolContext` with `lore_store=None`.
The early-return-empty branch in `query_lore.py:96-109` is now reachable
only from explicit test ctx-without-store fixtures.

### Verification — existing test coverage already covers the ACs

`tests/server/test_turn_context_sdk_wiring.py` (5 tests) and
`tests/agents/tools/test_query_lore.py` (≥8 tests including the
`test_otel_attrs_on_hit` and `test_otel_attrs_when_lore_store_unwired`
pair) collectively cover every AC on this story:

- **AC1** (lore_store threaded through): covered by
  `test_build_turn_context_populates_world_session_store_lore` —
  asserts `ctx.lore_store is sd.lore_store` (identity, not truthiness).
- **AC2** (`lore_store_wired=False` no longer fires in production):
  covered by `test_sdk_path_builds_toolcontext_with_real_ids_and_lore_store`
  driving the real `_run_narration_turn_sdk` and asserting
  `tool_ctx.lore_store is lore` on the dispatched ctx. The matching
  `test_otel_attrs_on_hit` checks `tool.lore.lore_store_wired is True` on
  the dispatch span.
- **AC3** (top-k fragments, not empty): covered by `test_query_lore.py::
  test_query_lore_returns_fragments_when_wired` (line 124+, asserts
  payload `lore_store_wired is True` and `fragments` populated).
- **AC4** (integration test through live orchestrator path, not stub):
  covered by `test_sdk_path_builds_toolcontext_with_real_ids_and_lore_store`
  which uses `_run_sdk_and_capture_ctx` to drive the production
  `Orchestrator.run_narration_turn` / `AnthropicSdkClient.complete_with_tools`
  path and capture the real `ToolContext` the registry dispatch built.
- **AC5** (OTEL spans participate in tool-loop): covered by
  `test_query_lore.py::test_otel_attrs_on_hit` (asserts `tool.read.query_lore`
  span fired with `tool.lore.lore_store_wired = True`).

All 16 tests across these two files pass on the current `develop`-derived
feature branch (`feat/61-1-wire-lorestore-toolcontext`) — confirmed via
`uv run pytest tests/server/test_turn_context_sdk_wiring.py
tests/agents/tools/test_query_lore.py -v` at 16 passed in 2.54s.

### Open question for SM / Dev

This story is functionally complete. Two paths forward — SM's call:

- **A.** Mark 61-1 done/closed-as-already-shipped, point at commit 06ad79c
  and the existing test coverage as evidence, and re-baseline 61-2's
  dependency declaration (61-2 said it depends on RAG actually working;
  RAG already works).
- **B.** Augment the test coverage with a stronger end-to-end assertion
  beyond what 24-10 shipped — e.g. a fixture that drives a multi-turn
  scenario, seeds the LoreStore via the real `seed_lore_from_char_creation`
  path, and asserts the narrator's prompt cost goes *down* once the RAG
  retrieval path replaces the wholesale-lore-dump. This is properly 61-6's
  shape (playtest validation) and would be premature here.

Recommend **A**. The wiring this story commissions is done; the cost-runaway
the story was framed against has a *different* root cause (Layer 2 / 61-2
snapshot slim — `room_states` + `journal` + `npcs` + `known_facts` +
`footnotes` + `belief_state` + `location_descriptions` flowing into the
Valley/Recency uncached). That's where the $313 actually came from. Wiring
RAG into ToolContext doesn't slim those fields out of the snapshot — only
61-2 does. So closing 61-1 as already-shipped lets the epic refocus on the
actual cost driver.

### Failure-mode-for-missing-lore_store question (story prompt §"Deliverables 2")

The story asked me to document the chosen failure mode for missing
`lore_store` (hard-fail vs `None` tolerated). Inspecting the live code,
this question is also already-answered by 24-10:

- `ToolContext.lore_store` keeps its `LoreStore | None = None` default so
  test fixtures can construct a `ToolContext` directly (the type signature
  matches `query_lore.py:96-109`'s tolerance contract).
- The production `_run_narration_turn_sdk` path at orchestrator.py:3472-3481
  *does* fail-loud (via `logger.warning("narrator.sdk_path.context_missing_ids
  — world_id=%s session_id=%s unexpectedly missing post-wiring; check
  _build_turn_context (should never fire in production).")`) when
  world_id/session_id come through unwired. This is the established
  fail-loud guard ADR-style for the entire context bundle (ids + stores).
- The matching test `test_sdk_path_context_missing_ids_still_fires_when_unwired`
  asserts that warning fires when the ids are absent.

A `lore_store`-specific hard-fail isn't currently in place; the
"context_missing_ids" warning is the umbrella guard. Per CLAUDE.md "No
Silent Fallbacks" the warning is sufficient because: (a) it's loud
(severity=WARNING, surfaces on the GM panel), (b) it tells the operator
which specific shape went unwired ("world_id=%s session_id=%s"), and (c)
the `narration.turn.lore_fragments` OTEL attribute on the per-turn span
(orchestrator.py:3531) gives the GM panel a second-line lie-detector. A
hard exception would crash the in-flight narration turn and disconnect
the player, which is worse than a loud warn + degraded retrieval — the
narrator still produces prose, the operator still sees the anomaly.

If 61-1 is reopened later (e.g. promoted from warn to hard-fail), the
right surface is the `context_missing_ids` branch at orchestrator.py:3474,
not a new `ToolContext.__post_init__` guard.

## TEA Assessment

**Tests Required:** No
**Reason:** Story is already implemented on develop. Commit 06ad79c
(`feat(24-10): wire world-grounding loaders + ToolContext fields at
bootstrap`, 2026-05-21) shipped the LoreStore→TurnContext→ToolContext
wiring this story commissions, two days before the epic-61 brief was
drafted. The epic brief was written against a stale read of the code.
All five ACs are already covered by existing tests in
`tests/server/test_turn_context_sdk_wiring.py` (5 tests) and
`tests/agents/tools/test_query_lore.py` (8+ tests); 16 of these pass
clean on the current feature branch. Writing a new failing test would
be either (a) a duplicate of existing coverage or (b) a fabricated
red — the production code is already green.

**Test Files:** None added.

**Tests Written:** 0 (already covered).
**Status:** N/A — bypass.

**Handoff:** Return to SM with recommendation to close 61-1 as
already-shipped (path A above). Cost-runaway root cause is 61-2's
snapshot slim, not 61-1's RAG wiring — closing 61-1 unblocks the
epic to focus on the actual driver without losing real coverage.

## Delivery Findings

### TEA (test design)

- **Conflict** (non-blocking): Epic-61 brief and story 61-1's
  acceptance criteria were drafted 2026-05-23 against a stale read
  of the codebase. The "RAG built, never wired into production"
  claim (epic-61 context.md §"Why the runaway was structurally
  possible" §1, plus 61-1 ACs 1–5) is no longer true on develop —
  commit 06ad79c (2026-05-21, 24-10) shipped the wiring. Affects
  `sprint/epic-61.yaml` (close 61-1 as already-shipped, re-baseline
  61-2's dependency note) and `sprint/context/context-epic-61.md`
  (the "Layer 1 — RAG production wiring (61-1)" section needs an
  amendment banner pointing at 06ad79c). The cost-runaway root cause
  framing for the *other* five layers stays correct; only 61-1's
  "this is unwired" premise was stale. *Found by TEA during pre-test
  topology check.*

- **Improvement** (non-blocking): The orchestrator.py:3472-3481
  fail-loud guard (`context_missing_ids` warning) covers the
  umbrella case but doesn't specifically fail on `lore_store=None`
  with ids present — a regression in `_build_turn_context` that
  forgets `lore_store=sd.lore_store` would slip past the existing
  guard. Affects `sidequest/agents/orchestrator.py:3474` (extend the
  conditional to also alarm when `context.lore_store is None` in
  production), and would deserve a matching unit test. Not in scope
  for 61-1 (because 61-1 is already done) but worth a 61-followup
  story if the user wants tighter defense-in-depth here. *Found by
  TEA while answering the failure-mode question.*

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

No deviations from spec at setup time.

### TEA (test design)

- **Bypassed test-writing phase:** Story prompt §"Deliverables for red
  phase" asked for two new failing tests (wiring/integration +
  construction-site unit). I wrote zero. Reason: the wiring this story
  commissions already shipped in 24-10 (commit 06ad79c, 2026-05-21);
  the production code is green; an artificially-failing test would
  test a fiction. Existing coverage is in
  `tests/server/test_turn_context_sdk_wiring.py` and
  `tests/agents/tools/test_query_lore.py` and passes 16/16 on the
  current feature branch. Recommending SM close 61-1 as
  already-shipped.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->
