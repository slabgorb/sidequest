# Story 50-5 — Scenario Clue Discovery via the Journal Pipeline

**Date:** 2026-05-13
**Story:** 50-5 — "Scenario: wire `discover_clue` to narration consumption (call site + SPAN_SCENARIO_ADVANCE fires in play)"
**Repos:** `sidequest-server`
**Workflow:** TDD
**Points:** 3
**Architectural ADR:** [ADR-100 Journal Pipeline Coherence](../../adr/100-journal-pipeline-coherence.md)
**Related ADRs:** [ADR-039](../../adr/039-narrator-structured-output.md), [ADR-053](../../adr/053-scenario-system.md), [ADR-087](../../adr/087-post-port-subsystem-restoration-plan.md)

## Summary

When a scenario is bound to a session, instruct the narrator about the undiscovered clue list and wire the existing `Footnote.fact_id` channel to the existing `ScenarioState.discover_clue()` method. On every matching footnote, also mint a canonical `KnownFact` on the active character — lighting up the P5-deferred `source`/`learned_turn` fields the journal model has been waiting for since the port.

This story closes **Seams A and B** from ADR-100. It introduces **no new protocol types, no new wire messages, no new handlers, and no UI changes**. The work is integration: one prompt section, one post-extraction hook, one shared integration test.

## Background

Per ADR-100, `ScenarioState.discover_clue()` (at `sidequest-server/sidequest/game/scenario_state.py:146`) is built, idempotent, and emits `SPAN_SCENARIO_ADVANCE`, but has zero production callers. The narrator already emits structured footnotes with a stable `fact_id` field (ADR-039), the server already forwards them through `NarrationPayload.footnotes` (`sidequest-server/sidequest/server/websocket_session_handler.py:2900`), and `Character.known_facts` already exists with `source` and `learned_turn` fields explicitly marked **"P5-deferred: used by scenario system"**. The wiring has been waiting.

## Goals

1. The narrator can see the active scenario's undiscovered clues in its prompt and is instructed to set `Footnote.fact_id` to the clue's id when narrating that clue's discovery.
2. The server, immediately after extracting footnotes from a narrator turn, scans them against the bound `ScenarioState.clue_graph`. For each match, it calls `ScenarioState.discover_clue(clue_id)`, causing `SPAN_SCENARIO_ADVANCE` to fire in live play (story exit criterion).
3. On the same match, the server mints a `KnownFact(content=footnote.summary, confidence='Discovered', source='ScenarioClue', learned_turn=current_interaction_turn)` on the active player's character.
4. The OTEL dashboard can verify scenario clue discovery from the span without inspecting narrator prose.
5. A single end-to-end integration test proves both seams fire on a real turn dispatch with a real narrator response containing a matching `fact_id`.

## Non-Goals

- **DAG enforcement.** Story 50-6 (already in backlog) gates discovery on `ClueNode.requires[]`. Story 50-5 explicitly allows orphan discoveries.
- **`JOURNAL_REQUEST`/`JOURNAL_RESPONSE` handler.** That is feeder story J-1 per ADR-100.
- **UI changes.** The journal continues to render `Suspected` from `useStateMirror.ts:194` until feeder story J-3 retires the hardcode. Players will not see the new `KnownFact` minting reflected in the UI until J-1+J-2+J-3 land. This is acceptable for 50-5 — the GM dashboard sees the span and the server-side `KnownFact` count immediately.
- **Belief state mutation, gossip propagation, accusation evaluation.** All ADR-053 restoration items at ADR-087 P2.
- **New wire messages, new sidecar JSON intents, new protocol types.**
- **Confidence enum promotion** on `KnownFact`. That is feeder story J-4.

## Architecture

### Component overview

```
              (existing)                          (existing)
narrator    ──prose+game_patch──>   orchestrator extract  ──>  forwarded_footnotes
                                                                      │
                                                                      │  ┌─ existing path ─> NarrationPayload.footnotes ──> UI
                                                                      │
                                                                      ▼
                                                          [NEW] scenario-clue scan
                                                                      │
                                                          ┌───────────┴───────────┐
                                                          ▼                       ▼
                                                 ScenarioState           Character.known_facts
                                                  .discover_clue           .append(KnownFact)
                                                  → SPAN_SCENARIO_ADVANCE   (source='ScenarioClue',
                                                                            confidence='Discovered')
```

### Change locations

| File | Change | LOC est. |
|------|--------|----------|
| `sidequest/agents/prompt_framework/core.py` | New `register_scenario_clues_section()` (mirrors `register_resource_section` pattern); injected in Late or Valley zone when `snapshot.scenario_state` is bound and has undiscovered clues. | ~30 |
| `sidequest/agents/prompt_framework/core.py` | Append two sentences to the existing footnote-protocol section (~line 350) instructing the narrator to set `fact_id` to a clue id when dramatizing one of the listed clues. | ~4 |
| `sidequest/server/websocket_session_handler.py` (~line 2911, immediately after `forwarded_footnotes` is built and before `NarrationPayload` is constructed) | New helper invocation that scans `forwarded_footnotes` against `snapshot.scenario_state.clue_graph`, calls `discover_clue` and mints `KnownFact` on matches. The helper itself lives in `sidequest/game/scenario_clue_consumption.py` (new file). | ~10 in handler + ~50 in helper |
| `sidequest/game/scenario_clue_consumption.py` (new file) | Pure function `apply_scenario_clue_discoveries(snapshot, footnotes, active_character_name) -> int` returning count of discoveries. Pure, testable in isolation. | ~50 |
| `sidequest/telemetry/spans/scenario.py` | No change required — `SPAN_SCENARIO_ADVANCE` already exists and is already emitted from inside `discover_clue`. | 0 |
| `tests/game/test_scenario_clue_consumption.py` (new) | Unit tests for the helper: no scenario bound → no-op; non-matching fact_id → no-op; matching → discover_clue called + KnownFact minted; duplicate match → idempotent (set semantics on `discovered_clues`, dedupe rules for known_facts documented below). | ~150 |
| `tests/integration/test_50_5_scenario_clue_in_play.py` (new) | The wiring test required by CLAUDE.md ("Every Test Suite Needs a Wiring Test"). Drives a real narrator turn through dispatch with a fake `claude -p` returning a `game_patch` with a `Footnote` whose `fact_id` matches a scenario clue. Asserts the span fired AND the `KnownFact` was minted with the right `source`/`confidence`. | ~120 |

### The helper's contract

```python
# sidequest/game/scenario_clue_consumption.py
def apply_scenario_clue_discoveries(
    snapshot: "GameSnapshot",
    footnotes: list[Footnote],
    active_character_name: str,
) -> int:
    """Scan footnotes against the bound scenario's clue graph; on match,
    fire discover_clue and mint a canonical KnownFact on the active
    character.

    Returns the number of clue discoveries applied this call.

    Behavior matrix:
      - snapshot.scenario_state is None             -> no-op, return 0
      - scenario_state.clue_graph has no nodes      -> no-op, return 0
      - no footnote.fact_id matches a ClueNode.id   -> no-op, return 0
      - match found, clue already in discovered_clues -> still call
        discover_clue (existing idempotent + emits duplicate=True span);
        DO NOT mint a duplicate KnownFact (dedupe by source+content)
      - match found, clue new                       -> call discover_clue
        (fires SPAN_SCENARIO_ADVANCE with duplicate=False) and append
        KnownFact(content=fn.summary, confidence='Discovered',
                  source='ScenarioClue',
                  learned_turn=snapshot.turn_manager.interaction)
        to the active character's known_facts.

    Pure function. Mutates snapshot.scenario_state.discovered_clues and
    the matching Character.known_facts in place. All side effects through
    existing methods — no direct field assignment.
    """
```

### The prompt section

When `snapshot.scenario_state` is bound and `clue_graph.nodes` has any entries not in `discovered_clues`, the prompt framework emits a Late-zone section approximately like:

```
<scenario_clues>
The following structural clues exist in this scenario and have not yet
been discovered. If your narration plausibly reveals one — through what
the players see, examine, are told, or overhear — emit a Footnote with
fact_id set to that clue's id.

  - id: candlestick_weapon
    description: A silver candlestick with traces of dried blood
    discovery_method: physical_search
    locations: [drawing_room, evidence_table]

  - id: butler_alibi_contradicted
    description: The butler was not in the pantry at 9pm
    discovery_method: questioning
    locations: [interview_butler]

Set fact_id only when the clue is genuinely revealed in your narration
— not when merely hinted at. Discovery should follow plausibly from the
player's action.
</scenario_clues>
```

The exact wording is the Dev's call within the bounds of: (1) list every undiscovered clue with id/description/discovery_method/locations; (2) instruct the narrator to set `fact_id` to the clue id only on genuine discovery; (3) follow the existing footnote-protocol prose's tone.

### Idempotency and dedupe

- **`ScenarioState.discover_clue`** is already idempotent — `discovered_clues` is a set, and the span attribute `duplicate=True` is set on repeat calls (`scenario_state.py:155`). No change needed.
- **`Character.known_facts`** uses list semantics — duplicate-prevention is the helper's responsibility. The helper checks for an existing `KnownFact` with `source='ScenarioClue'` and `content==fn.summary` before appending. (Future: J-4 promotes `confidence` to an enum and may add a stable id to `KnownFact`; until then content+source is the dedupe key.)
- **Multiple footnotes in one turn matching the same clue** → first call discovers and mints, second call is a duplicate (span emits `duplicate=True`, no second `KnownFact`).
- **Same clue rediscovered next turn** → narrator should emit the footnote with `is_new=False` per ADR-039, but the helper does not gate on `is_new` (the narrator is allowed to be wrong); `discover_clue` is idempotent, the `KnownFact` dedupe check prevents duplicate entry.

### Multiplayer correctness

`active_character_name` is supplied from the existing dispatch context (`sd.player_name` is already available at the call site). The `KnownFact` is minted on the actor's character only — not broadcast to other characters' `known_facts`. Other players see the clue via the canonical `Footnote.fact_id` flowing through `NarrationPayload.footnotes` to all clients (ADR-036 projection rules govern visibility). When the C-seam (J-1) lands, each player's `JOURNAL_RESPONSE` will show only their own character's `known_facts`, which is the intended per-character journal isolation.

### OTEL telemetry

- **`SPAN_SCENARIO_ADVANCE`** — fires from `discover_clue()`. Attributes: `clue_id, duplicate, guilty_npc, discovered_total`. Already wired. Required by story exit criterion.
- **No new spans for this story.** The `KnownFact` mint piggybacks on the same scenario span. A separate `journal.entry_minted` span is deliberately deferred to a later story when journal entries have multiple sources to disambiguate (gossip-derived, observation-derived, scenario-derived, NPC-told).

## Acceptance Criteria

1. Running a turn against a session bound to a scenario, with the narrator returning a `game_patch` whose `footnotes[]` contains an entry with `fact_id` matching an undiscovered `ClueNode.id`:
   - `SPAN_SCENARIO_ADVANCE` is emitted with `duplicate=False`, the matching `clue_id`, and `discovered_total >= 1`.
   - The active player's character has a new `KnownFact` in `known_facts` with `source == "ScenarioClue"`, `confidence == "Discovered"`, `learned_turn == snapshot.turn_manager.interaction`, and `content == footnote.summary`.
2. Running a turn against a session **not** bound to a scenario: no scenario-clue spans are emitted and no `KnownFact`s with `source == "ScenarioClue"` are minted. Existing footnote-forwarding behavior is unchanged.
3. Running a turn with a `fact_id` that **does not** match any `ClueNode.id`: same as (2). The footnote is still forwarded to the UI via `NarrationPayload.footnotes` unchanged.
4. A second footnote in the same turn (or a footnote in a subsequent turn) referencing the **same** `clue_id`:
   - `SPAN_SCENARIO_ADVANCE` is emitted with `duplicate=True`.
   - No second `KnownFact` is appended.
5. The narrator prompt includes a `<scenario_clues>` block (or equivalent named section) listing every undiscovered clue when `scenario_state` is bound. The block is absent when `scenario_state` is unbound or all clues are discovered.
6. The footnote-protocol prose has been amended to instruct the narrator about `fact_id`-on-clue-discovery.
7. Unit test suite `tests/game/test_scenario_clue_consumption.py` covers the helper's behavior matrix.
8. Integration test `tests/integration/test_50_5_scenario_clue_in_play.py` proves end-to-end wiring: real dispatch path, fake narrator output, span assertion, `KnownFact` assertion.
9. `uv run ruff check .`, `uv run pytest -v`, and `uv run pyright` all pass in `sidequest-server`.

## Open Risks

- **Narrator emits a `fact_id` that doesn't match any clue.** Mitigation: the helper only acts on matches; non-matching footnotes flow through unchanged. This is documented in the helper's docstring and tested.
- **Narrator emits a clue's `fact_id` for a footnote whose `summary` doesn't actually describe the clue.** Mitigation: not technically possible to fully prevent — the narrator is asked to be honest. The helper trusts the `fact_id` mark. The GM dashboard (via `SPAN_SCENARIO_ADVANCE` content) will surface the mismatch for inspection; future continuity-validator work (ADR-087 P1) can flag it.
- **The narrator ignores the prompt and never sets `fact_id`.** Mitigation: a clue is never discovered, the mystery stalls, the GM dashboard shows zero scenario advances. This is observable in play and surfaceable to Keith. It is *not* a silent failure — the absence of spans is the loud signal.
- **A scenario clue is discovered before the player's "discovery action" is plausible** (narrator over-discloses). Mitigation: prompt instructs "Set fact_id only when the clue is genuinely revealed... Discovery should follow plausibly from the player's action." This is a tuning concern, not an architectural one; the DAG gate (50-6) reduces severity by preventing early-stage clues from being discovered before their prerequisites.

## Test Plan

Per CLAUDE.md "Every Test Suite Needs a Wiring Test."

### Unit tests (`tests/game/test_scenario_clue_consumption.py`)

| Test | Asserts |
|------|---------|
| `test_no_scenario_state_is_noop` | Helper returns 0; no exceptions. |
| `test_empty_clue_graph_is_noop` | Helper returns 0 even when scenario_state is bound. |
| `test_nonmatching_fact_id_is_noop` | Footnote with `fact_id='unrelated'` against scenario with `ClueNode.id='real_clue'` returns 0. |
| `test_matching_fact_id_discovers_clue` | Footnote with matching `fact_id` causes `clue_id in scenario_state.discovered_clues`. |
| `test_matching_fact_id_mints_known_fact` | Footnote with matching `fact_id` appends `KnownFact(source='ScenarioClue', confidence='Discovered', learned_turn=N, content=fn.summary)` to active character. |
| `test_duplicate_match_does_not_double_mint` | Two footnotes in the same call with the same matching `fact_id` produce one `KnownFact`, but `discover_clue` is called once (set semantics) or twice with the second a duplicate (acceptable, span machinery handles it). |
| `test_multiple_distinct_matches` | Two footnotes with two different matching `fact_id`s produce two `KnownFact`s. |
| `test_inactive_character_unaffected` | Multi-character party: only the active character's `known_facts` is mutated. |
| `test_span_attributes` | `SPAN_SCENARIO_ADVANCE` attributes include `clue_id`, `duplicate`, `guilty_npc`, `discovered_total`. |

### Integration test (`tests/integration/test_50_5_scenario_clue_in_play.py`)

Drives the real dispatch path with a fake `claude -p` subprocess returning a canned response. Asserts:

1. Span captured via test SpanCapture fixture matches `SPAN_SCENARIO_ADVANCE` with the expected `clue_id`.
2. The session's snapshot has the matching character with the expected `KnownFact` after the turn returns.
3. The `NarrationPayload` broadcast to the player includes the original footnote (footnote forwarding is **not** suppressed by scenario consumption).

## Definition of Done

- All acceptance criteria pass.
- All unit + integration tests green.
- Lint, type-check, and full test suite pass.
- Story session file has Dev Assessment, TEA Assessment, and ScrumMaster handoff complete.
- PR merged to `develop` (server repo uses gitflow per `repos.yaml`).
- `pf sprint story finish 50-5` run from orchestrator.
- ADR-100 implementation-status remains `partial` (seams A+B closed, seam C still owed).
